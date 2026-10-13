#!/usr/bin/env python3
"""Mirror external documentation into sources/ with provenance.

    python3 tools/ingest.py                 # fetch + convert every mirror source
    python3 tools/ingest.py --only opencode-v1-skills nrp-llm-managed
    python3 tools/ingest.py --group expanse
    python3 tools/ingest.py --check         # report upstream changes/drift, write nothing
    python3 tools/ingest.py --index         # only regenerate sources/INDEX.md

Inputs  : sources/registry.toml   (human-edited: WHAT to mirror, from WHERE, at which ref)
Outputs : sources/<group>/<id>.md (generated local copies; gitignored, never committed)
          sources/lock.json       (machine-written: resolved commit, content hashes, dates)
          sources/INDEX.md        (generated catalogue of mirrors + link-only sources)

status = "auto"  -> file is regenerated on every run.
status = "fixed" -> file was hand-repaired; it is NEVER overwritten. If the upstream content hash
                    changes, the new conversion is written to <id>.upstream.md and reported as
                    DRIFT so a human/agent can re-apply the fix. See sources/README.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tomllib
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from convert import convert_html, convert_md, convert_mdx, convert_yaml_dir  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]   # SDSC/kb
SRC = ROOT / "sources"
REGISTRY = SRC / "registry.toml"
LOCK = SRC / "lock.json"
# Fingerprint of the conversion code: when converters improve, every auto source is regenerated.
CONVERTER = hashlib.sha256((Path(__file__).parent / "convert.py").read_bytes()).hexdigest()[:16]
UA = {"User-Agent": "hpcgpt-sdsc-kb-ingest/1.0 (+https://github.com/mkandes/hpcgpt-cli)"}


# --------------------------------------------------------------------------- registry
def load_registry() -> tuple[dict, list[dict]]:
    reg = tomllib.loads(REGISTRY.read_text())
    groups = reg.get("groups", {})
    sources = []
    for s in reg.get("source", []):
        merged = {**groups.get(s.get("group", ""), {}), **s}
        merged.setdefault("mode", "mirror")
        merged.setdefault("status", "auto")
        if merged["mode"] == "mirror":
            page = merged.get("page") or merged.get("path", "").rsplit(".", 1)[0]
            merged.setdefault("url", merged.get("url_template", "").format(page=page) or None)
        sources.append(merged)
    ids = [s["id"] for s in sources]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        sys.exit(f"duplicate ids in registry: {sorted(dupes)}")
    return groups, sources


def recipe(s: dict) -> str:
    """Converter code + this source's conversion settings; a change forces re-rendering."""
    keys = ("format", "selector", "link_base", "columns", "prefix", "path", "title")
    blob = CONVERTER + json.dumps({k: s.get(k) for k in keys}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def dest_path(s: dict) -> Path:
    return SRC / s["group"] / f"{s['id']}.md"


# --------------------------------------------------------------------------- fetching
def http_get(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


_gh_token: str | None = None


def gh_headers() -> dict:
    global _gh_token
    if _gh_token is None:
        _gh_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        if not _gh_token:
            try:
                _gh_token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
            except FileNotFoundError:
                _gh_token = ""
    return {"Authorization": f"Bearer {_gh_token}"} if _gh_token else {}


_commit_cache: dict[tuple, str] = {}


def resolve_commit(s: dict) -> str | None:
    """Resolve a branch/tag ref to an immutable commit SHA so every fetch is reproducible."""
    kind, ref = s.get("kind"), s.get("ref")
    key = (kind, s.get("repo"), ref)
    if key in _commit_cache:
        return _commit_cache[key]
    sha = None
    if kind == "github":
        data = json.loads(http_get(f"https://api.github.com/repos/{s['repo']}/commits/{ref}", gh_headers()))
        sha = data["sha"]
    elif kind == "gitlab":
        proj = urllib.parse.quote(s["repo"], safe="")
        data = json.loads(http_get(f"{s['host']}/api/v4/projects/{proj}/repository/commits/{urllib.parse.quote(ref, safe='')}"))
        sha = data["id"]
    _commit_cache[key] = sha
    return sha


def raw_url(s: dict, commit: str | None) -> str:
    path = s.get("prefix", "") + s["path"] if s.get("path") else None
    if s.get("format") == "yaml-dir" and s["kind"] == "gitlab" and "path" in s and not path.endswith((".yaml", ".yml")):
        return f"{s['host']}/{s['repo']}/-/tree/{commit}/{path}"
    if s["kind"] == "github":
        return f"https://raw.githubusercontent.com/{s['repo']}/{commit}/{path}"
    if s["kind"] == "gitlab":
        return f"{s['host']}/{s['repo']}/-/raw/{commit}/{path}"
    return s.get("fetch_url") or s["url"]


def list_dir(s: dict, commit: str) -> list[str]:
    """Repo-relative paths of the files directly inside prefix+path (a directory)."""
    d = (s.get("prefix", "") + s["path"]).rstrip("/")
    if s["kind"] == "github":
        items = json.loads(http_get(f"https://api.github.com/repos/{s['repo']}/contents/{d}?ref={commit}", gh_headers()))
        return [it["path"] for it in items if it["type"] == "file"]
    if s["kind"] == "gitlab":
        proj = urllib.parse.quote(s["repo"], safe="")
        q = urllib.parse.urlencode({"path": d, "ref": commit, "per_page": 100})
        items = json.loads(http_get(f"{s['host']}/api/v4/projects/{proj}/repository/tree?{q}"))
        return [it["path"] for it in items if it["type"] == "blob"]
    raise ValueError("yaml-dir needs kind github or gitlab")


def fetch_and_convert(s: dict) -> tuple[str, str, str | None, list[str]]:
    """Return (markdown, upstream_sha256, commit, warnings)."""
    commit = resolve_commit(s)
    if s["format"] == "yaml-dir":
        docs, digest = {}, hashlib.sha256()
        for path in sorted(list_dir(s, commit)):
            if path.endswith((".yaml", ".yml")):
                blob = http_get(raw_url({**s, "prefix": "", "path": path}, commit))
                digest.update(path.encode() + b"\0" + blob)
                docs[path.rsplit("/", 1)[-1]] = blob.decode("utf-8", errors="replace")
        md, warn = convert_yaml_dir(docs, s.get("title", s["id"]), s.get("columns", ["id"]))
        return md, digest.hexdigest(), commit, warn
    url = raw_url(s, commit)
    blob = http_get(url, gh_headers() if s["kind"] == "github" else None)
    upstream_hash = hashlib.sha256(blob).hexdigest()
    text = blob.decode("utf-8", errors="replace")
    fmt = s["format"]
    if fmt == "md":
        md, warn = convert_md(text, s.get("link_base"))
    elif fmt == "mdx":
        md, warn = convert_mdx(text, s.get("link_base"))
    elif fmt == "html":
        md, warn = convert_html(text, s["url"], s.get("selector"))
        # live HTML carries volatile markup (nonces, timestamps): hash the converted text instead
        upstream_hash = hashlib.sha256(md.encode()).hexdigest()
    else:
        raise ValueError(f"unknown format {fmt}")
    return md, upstream_hash, commit, warn


# --------------------------------------------------------------------------- output
def render(s: dict, body: str, commit: str | None, retrieved: str) -> str:
    ref = s.get("ref")
    ref_str = f"{ref} @ {commit[:12]}" if ref and commit else (ref or "live page")
    fm = [
        "---",
        "origin: external",
        f"source_id: {s['id']}",
        f"title: {json.dumps(s.get('title', s['id']))}",
        f"source_url: {s['url']}",
        f"fetched_from: {raw_url(s, commit)}",
        f"ref: {json.dumps(ref_str)}",
        f"retrieved: {retrieved}",
        f"status: {s['status']}",
        f"license: {json.dumps(s.get('license', 'unknown'))}",
        "---",
    ]
    banner = (
        f"> **EXTERNAL SOURCE (mirrored, not written by us).** Upstream: <{s['url']}> "
        f"({ref_str}, retrieved {retrieved}). Generated by `tools/ingest.py`; "
        f"do not edit, instead change `sources/registry.toml` (see `sources/README.md`)."
    )
    if s["status"] == "fixed":
        banner = banner.replace("do not edit, instead", "HAND-FIXED copy (status=fixed); re-apply fixes if upstream drifts, or")
    return "\n".join(fm) + "\n\n" + banner + "\n\n" + body


def load_lock() -> dict:
    return json.loads(LOCK.read_text()) if LOCK.exists() else {}


def save_lock(lock: dict) -> None:
    LOCK.write_text(json.dumps(dict(sorted(lock.items())), indent=2) + "\n")


def write_index(groups: dict, sources: list[dict], lock: dict) -> None:
    lines = [
        "---", "origin: generated", "---", "",
        "# External source index",
        "",
        "> **GENERATED** by `tools/ingest.py` from `sources/registry.toml`. Do not edit by hand.",
        "> Mirrored = a local Markdown copy exists (with provenance frontmatter). Link = consult online.",
        "",
    ]
    order = list(groups) + sorted({s["group"] for s in sources} - set(groups))
    for g in order:
        members = [s for s in sources if s["group"] == g]
        if not members:
            continue
        meta = groups.get(g, {})
        lines += [f"## {meta.get('title', g)}", ""]
        if meta.get("description"):
            lines += [meta["description"], ""]
        lines += ["| Source | Mode | Local copy | Ref / retrieved | Notes |", "|---|---|---|---|---|"]
        for s in members:
            lk = lock.get(s["id"], {})
            if s["mode"] == "mirror":
                p = dest_path(s).relative_to(SRC)
                local = f"[`{p}`]({p})" if dest_path(s).exists() else "_(not fetched yet)_"
                mode = "mirror" + (" **(fixed)**" if s["status"] == "fixed" else "")
                refinfo = f"{s.get('ref', 'live')} · {lk.get('retrieved', '-')}"
            else:
                local, mode, refinfo = "-", "link", "-"
            note = s.get("note", "").replace("|", "\\|")
            lines.append(f"| [{s.get('title', s['id'])}]({s['url']}) | {mode} | {local} | {refinfo} | {note} |")
        lines.append("")
    (SRC / "INDEX.md").write_text("\n".join(lines))


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="+", metavar="ID")
    ap.add_argument("--group", nargs="+")
    ap.add_argument("--check", action="store_true", help="report changes/drift without writing")
    ap.add_argument("--index", action="store_true", help="only regenerate sources/INDEX.md")
    args = ap.parse_args()

    groups, sources = load_registry()
    lock = load_lock()
    if args.index:
        write_index(groups, sources, lock)
        return 0

    todo = [s for s in sources if s["mode"] == "mirror"]
    if args.only:
        unknown = set(args.only) - {s["id"] for s in todo}
        if unknown:
            sys.exit(f"unknown mirror ids: {sorted(unknown)}")
        todo = [s for s in todo if s["id"] in args.only]
    if args.group:
        todo = [s for s in todo if s["group"] in args.group]

    today = dt.date.today().isoformat()
    failures = drift = changed = 0
    for s in todo:
        sid, out = s["id"], dest_path(s)
        try:
            md, h, commit, warn = fetch_and_convert(s)
        except Exception as e:  # noqa: BLE001 - report and continue with the rest
            failures += 1
            print(f"FAIL   {sid}: {e}")
            continue
        prev = lock.get(sid, {})
        is_new = prev.get("upstream_sha256") != h
        reconvert = prev.get("converter") != recipe(s)
        tag = "CHANGE" if is_new and prev else ("NEW   " if not prev else "same  ")
        for w in warn:
            print(f"  warn {sid}: {w}")

        if s["status"] == "fixed":
            base = prev.get("fixed_from_sha256") or prev.get("upstream_sha256")
            if base and base != h:
                drift += 1
                print(f"DRIFT  {sid}: upstream changed since hand-fix -> {out.with_suffix('.upstream.md').name}")
                if not args.check:
                    out.with_suffix(".upstream.md").write_text(render(s, md, commit, today))
            else:
                print(f"fixed  {sid}: unchanged upstream")
            if not args.check:
                prev.setdefault("fixed_from_sha256", base or h)
                prev.update(last_checked=today, latest_upstream_sha256=h)
                lock[sid] = prev
            continue

        if reconvert and not is_new:
            tag = "RECONV"
        print(f"{tag} {sid}")
        if args.check:
            changed += is_new
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        if is_new or reconvert or not out.exists():
            out.write_text(render(s, md, commit, today))
            changed += 1
            lock[sid] = {
                "commit": commit, "upstream_sha256": h, "converter": recipe(s),
                "retrieved": today if is_new or not prev else prev.get("retrieved", today),
                "path": str(out.relative_to(ROOT)), "warnings": warn,
            }
        else:
            lock[sid]["last_checked"] = today

    if not args.check:
        save_lock(lock)
        write_index(groups, sources, lock)
    print(f"\n{len(todo)} sources, {changed} changed, {drift} drifted (fixed), {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
