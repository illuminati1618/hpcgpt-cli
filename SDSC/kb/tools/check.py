#!/usr/bin/env python3
"""KB lint: doc frontmatter, source ids, local copies, links.   python3 SDSC/kb/tools/check.py

Rules (see SDSC/kb/AGENTS.md):
  <topic>/**/*.md, glossary.md   origin: kb, title, author, updated, verified; body starts with the SDSC KB DOC banner;
                                 every id in `sources:` exists in sources/registry.toml
  docs never link into sources/<group>/ (local, gitignored copies): link the upstream URL
  sources/<group>/*.md (if present locally)  origin: external, source_id registered as a mirror, expected path
  relative Markdown links in README.md, AGENTS.md, sources/README.md and every doc resolve
Exit 1 on any error.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   # SDSC/kb
sys.path.insert(0, str(Path(__file__).parent))
from ingest import dest_path, load_registry  # noqa: E402

BANNER = "> **SDSC KB DOC"
NOT_DOCS = {"sources", "tools"}
errors: list[str] = []


def err(path: Path, msg: str) -> None:
    errors.append(f"{path.relative_to(ROOT)}: {msg}")


def frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text()
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    fm = {}
    key = None
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = m.group(2).strip().strip('"')
        elif key and line.strip().startswith("- "):
            fm[key] = (fm[key] if isinstance(fm[key], list) else []) + [line.strip()[2:].strip()]
    return fm, text[end + 4 :].lstrip("\n")


def gfm_anchors(path: Path) -> set[str]:
    """GitHub-style heading slugs of a Markdown file (code fences ignored, duplicates get -1, -2...)."""
    text = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
    seen: dict[str, int] = {}
    out = set()
    for h in re.findall(r"^#{1,6}\s+(.+?)\s*#*$", text, flags=re.M):
        h = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", h)          # link text only
        slug = re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-")
        n = seen.get(slug, 0)
        out.add(slug if n == 0 else f"{slug}-{n}")
        seen[slug] = n + 1
    return out


def docs() -> list[Path]:
    """Our docs: every .md except README/AGENTS and anything under sources/ or tools/."""
    return sorted(p for p in ROOT.rglob("*.md")
                  if p.relative_to(ROOT).parts[0] not in NOT_DOCS and p.name not in ("README.md", "AGENTS.md"))


def main() -> int:
    _, sources = load_registry()
    by_id = {s["id"]: s for s in sources}
    mirrors = {s["id"]: s for s in sources if s["mode"] == "mirror"}

    # --- KB docs ------------------------------------------------------------------------
    for p in docs():
        fm, body = frontmatter(p)
        if fm.get("origin") != "kb":
            err(p, "missing `origin: kb` frontmatter")
        for k in ("title", "author", "updated", "verified"):
            if not fm.get(k):
                err(p, f"missing `{k}:` frontmatter")
        if not body.startswith(BANNER):
            err(p, f"body must start with the banner line '{BANNER} ...'")
        cited = fm.get("sources", [])
        for sid in cited if isinstance(cited, list) else [cited]:
            if sid and sid not in by_id:
                err(p, f"cites unknown source id `{sid}`")

    # --- external mirrors ---------------------------------------------------------------
    for p in sorted((ROOT / "sources").rglob("*.md")):
        rel = p.relative_to(ROOT / "sources")
        if rel.parts == ("README.md",):
            continue
        fm, _ = frontmatter(p)
        if rel.parts == ("INDEX.md",):
            if fm.get("origin") != "generated":
                err(p, "INDEX.md must be `origin: generated`")
            continue
        if p.name.endswith(".upstream.md"):
            continue  # drift artefact of a fixed source, reported by ingest
        sid = fm.get("source_id")
        if fm.get("origin") != "external":
            err(p, "files under sources/ must have `origin: external` (write docs in a topic folder)")
        elif sid not in mirrors:
            err(p, f"source_id `{sid}` is not a mirror entry in registry.toml")
        elif dest_path(mirrors[sid]).resolve() != p.resolve():
            err(p, f"expected at {dest_path(mirrors[sid]).relative_to(ROOT)}")

    # --- relative links -----------------------------------------------------------------
    link_roots = [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "sources" / "README.md", *docs()]
    for p in link_roots:
        if not p.exists():
            continue
        text = re.sub(r"```.*?```", "", p.read_text(), flags=re.S)
        for target in re.findall(r"\]\(([^)\s]+)\)", text):
            if re.match(r"^[a-z]+:|^#|^<", target):
                continue
            path, _, anchor = target.partition("#")
            dest = (p.parent / path) if path else p
            if path and dest.suffix == ".md" and dest.name != "README.md" \
                    and dest.resolve().is_relative_to(ROOT / "sources"):
                err(p, f"links a local source copy (gitignored) -> {target}; link the upstream URL")
                continue
            if path and not dest.exists():
                err(p, f"broken relative link -> {target}")
            elif anchor and dest.suffix == ".md" and anchor not in gfm_anchors(dest):
                err(p, f"broken anchor -> {target}")

    for e in errors:
        print("ERROR", e)
    print(f"check: {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
