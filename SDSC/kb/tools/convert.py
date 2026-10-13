"""Converters: upstream document (md | mdx | html) -> clean GitHub-flavoured Markdown.

Pure functions, no I/O except the pandoc subprocess. Each returns (markdown, warnings).
Design notes live in sources/README.md ("Converters").
"""
from __future__ import annotations

import json
import re
import subprocess
from urllib.parse import urljoin

FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")


def fence_step(line: str, state: str | None) -> tuple[bool, str | None]:
    """CommonMark-ish fence tracking. `state` is the opening fence run (e.g. "```") or None.

    Returns (is_fence_line, new_state). A closing fence must use the same character, be at least as long
    as the opener and carry no info string; ```` ```bash ```` inside an open block is content, not a close.
    """
    m = FENCE.match(line)
    if not m:
        return False, state
    run, info = m.group(2), m.group(3).strip()
    if state is None:
        return True, run
    if run[0] == state[0] and len(run) >= len(state) and not info:
        return True, None
    return False, state


# --------------------------------------------------------------------------- helpers
def split_frontmatter(text: str) -> tuple[dict, str]:
    """Strip a leading YAML frontmatter block; return ({title, description}, body)."""
    meta: dict = {}
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            block, text = text[4:end], text[end + 4 :].lstrip("\n")
            for line in block.splitlines():
                m = re.match(r"^(title|description):\s*(.*)$", line)
                if m:
                    meta[m.group(1)] = m.group(2).strip().strip("'\"")
    return meta, text


def absolutize_links(md: str, link_base: str | None) -> str:
    """Rewrite root-relative markdown links `](/x)` to `](<link_base>/x)` outside code fences."""
    if not link_base:
        return md
    out, in_fence = [], None
    for line in md.splitlines():
        was_in = in_fence
        _, in_fence = fence_step(line, in_fence)
        if not (was_in or in_fence):
            line = re.sub(r"\]\((/[^)\s]*)\)", lambda mm: f"]({urljoin(link_base, mm.group(1))})", line)
        out.append(line)
    return "\n".join(out)


def heading(meta: dict) -> str:
    parts = []
    if meta.get("title"):
        parts.append(f"# {meta['title']}")
    if meta.get("description"):
        parts.append(f"_{meta['description']}_")
    return "\n\n".join(parts) + ("\n\n" if parts else "")


# --------------------------------------------------------------------------- md
def convert_md(text: str, link_base: str | None = None) -> tuple[str, list[str]]:
    meta, body = split_frontmatter(text)
    head = heading(meta) if meta.get("title") and not re.match(r"^#\s", body) else ""
    return head + absolutize_links(body, link_base).strip() + "\n", []


# --------------------------------------------------------------------------- mdx
ATTR = re.compile(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|\{([^}]*)\})')
ADMONITION_OPEN = re.compile(r"^:::(note|tip|caution|danger|warning|info|important)(?:\[(.*?)\])?\s*$")
KNOWN_DROP = {"Steps", "Tabs", "CardGrid", "Fragment"}           # keep content, drop tag
KNOWN_SELF_CLOSING_DROP = {"ClientPicker", "Icon", "Badge"}       # drop entirely
# data-driven components whose content is NOT in the page source (rendered from a collection)
DATA_COMPONENTS = {"ModelFeatureMatrix", "ModelBenchmarkChart", "ModelCard"}
INLINE_BADGE = re.compile(r"<Badge\b[^>]*/>")


def _quoted(line: str, depth: int) -> str:
    """Prefix a line with `depth` blockquote markers (no trailing space on blank lines)."""
    if not depth:
        return line
    return ("> " * depth + line) if line.strip() else ("> " * depth).rstrip()


def _attrs(tag: str) -> dict:
    return {m.group(1): next(g for g in m.groups()[1:] if g is not None) for m in ATTR.finditer(tag)}


def convert_mdx(text: str, link_base: str | None = None) -> tuple[str, list[str]]:
    """Normalise Astro/Starlight MDX to plain Markdown.

    Fence-aware: `import`/`export` lines and JSX inside ``` blocks are code and are kept verbatim.
    Unknown components have their tag stripped (content kept) and are reported as warnings.
    """
    meta, body = split_frontmatter(text)
    warnings: list[str] = []
    out: list[str] = []
    in_fence = None          # fence char while inside a code block
    quote_depth = 0          # >0 while inside an admonition/Aside -> prefix "> "
    skipping_tag = None      # multi-line self-closing tag being dropped
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        stripped = line.strip()

        if skipping_tag:
            if stripped.endswith("/>") or stripped.endswith(f"</{skipping_tag}>"):
                skipping_tag = None
            continue

        is_fence, new_state = fence_step(line, in_fence)
        if is_fence or in_fence:
            in_fence = new_state
            out.append(_quoted(line, quote_depth))
            continue
        if in_fence:
            out.append(_quoted(line, quote_depth))
            continue

        # ---- outside code fences ------------------------------------------------
        if INLINE_BADGE.search(line):
            line = INLINE_BADGE.sub(lambda mb: f"**[{_attrs(mb.group(0)).get('text', '')}]**", line)
            stripped = line.strip()
        if re.match(r"^export\s+(const|let|function|default)\b", stripped):
            # component-level JS (e.g. `export const allModels = await getCollection(...)`): drop the statement
            while i < len(lines) and lines[i].strip() and not stripped.rstrip().endswith(";"):
                stripped = lines[i].strip(); i += 1
            continue
        lb = re.match(r"^<LinkButton\b([^>]*)>(.*?)(</LinkButton>)?$", stripped)
        if lb:
            href, text_parts = _attrs(lb.group(1)).get("href", ""), [lb.group(2).strip()]
            if not lb.group(3):
                while i < len(lines) and "</LinkButton>" not in lines[i]:
                    text_parts.append(lines[i].strip()); i += 1
                if i < len(lines):
                    text_parts.append(lines[i].split("</LinkButton>")[0].strip()); i += 1
            indent = re.match(r"^\s*", line).group(0)
            out.append(_quoted(f"{indent}[{' '.join(t for t in text_parts if t)}]({href})", quote_depth))
            continue
        if re.match(r"^import\s.+\sfrom\s.+;?$", stripped) or re.match(r"^import\s+['\"].+['\"];?$", stripped):
            continue

        am = ADMONITION_OPEN.match(stripped)
        if am:
            kind, title = am.group(1).upper(), am.group(2)
            out.append(("> " * quote_depth) + f"> **{kind}{': ' + title if title else ''}**")
            out.append(("> " * quote_depth) + ">")
            quote_depth += 1
            continue
        if stripped == ":::" and quote_depth:
            quote_depth -= 1
            out.append("")
            continue

        tm = re.match(r"^<(/?)([A-Z][A-Za-z0-9]*)\b(.*?)(/?)>\s*$", stripped)
        if not tm and re.match(r"^<([A-Z][A-Za-z0-9]*)\b", stripped) and not stripped.endswith(">"):
            # multi-line opening tag: gather until '>' so attributes are parsed
            buf = [stripped]
            while i < len(lines) and not lines[i].strip().endswith(">"):
                buf.append(lines[i].strip()); i += 1
            if i < len(lines):
                buf.append(lines[i].strip()); i += 1
            stripped = " ".join(buf)
            tm = re.match(r"^<(/?)([A-Z][A-Za-z0-9]*)\b(.*?)(/?)>\s*$", stripped, re.S)
        if tm:
            closing, name, rest, selfclose = tm.groups()
            a = _attrs(rest)
            pre = "> " * quote_depth
            if name in ("Aside", "Callout"):
                if closing:
                    quote_depth = max(0, quote_depth - 1); out.append("")
                else:
                    kind = a.get("type", "note").upper()
                    out.append(pre + f"> **{kind}{': ' + a['title'] if a.get('title') else ''}**")
                    out.append(pre + ">")
                    quote_depth += 1
            elif name == "TabItem":
                if not closing:
                    out.append(pre + f"**{a.get('label', 'Tab')}:**")
                    out.append(pre)
            elif name == "ConfigDrawer":
                if not closing:
                    label = a.get("label", "Configuration")
                    note = f" ({a['note']})" if a.get("note") else ""
                    out.append(pre + f"**{label}**{note}")
                    out.append(pre)
            elif name in ("LinkCard", "Card") and not closing:
                t = a.get("title", "")
                out.append(pre + (f"- [{t}]({a['href']})" if a.get("href") else f"**{t}**"))
                if a.get("description"):
                    out.append(pre + f"  {a['description']}")
            elif name == "LinkButton":
                # multi-line opening tag: link text follows on the next lines until </LinkButton>
                if not closing:
                    text_parts = []
                    while i < len(lines) and "</LinkButton>" not in lines[i]:
                        text_parts.append(lines[i].strip()); i += 1
                    if i < len(lines):
                        text_parts.append(lines[i].split("</LinkButton>")[0].strip()); i += 1
                    out.append(pre + f"[{' '.join(t for t in text_parts if t)}]({a.get('href', '')})")
            elif name in DATA_COMPONENTS:
                out.append(pre + f"> _[`<{name}>`: data-driven widget not present in the page source; see the site or the mirrored data collection]_")
            elif name in KNOWN_SELF_CLOSING_DROP or name in KNOWN_DROP or name in ("Card", "LinkCard"):
                pass
            else:
                warnings.append(f"unknown MDX component <{name}> (tag stripped, content kept)")
            continue
        if re.match(r"^<([A-Z][A-Za-z0-9]*)\b", stripped):
            name = re.match(r"^<([A-Z][A-Za-z0-9]*)", stripped).group(1)
            if not stripped.endswith("/>"):
                skipping_tag = name
            warnings.append(f"dropped multi-line component <{name}>")
            continue

        out.append(_quoted(line, quote_depth))

    md = "\n".join(out)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return heading(meta) + absolutize_links(md, link_base).strip() + "\n", sorted(set(warnings))


# --------------------------------------------------------------------------- html
def _slug(text: str) -> str:
    s = re.sub(r"[^\w\- ]", "", text.strip().lower())
    return re.sub(r"\s", "-", s)


def convert_html(text: str, base_url: str, selector: str | None = None) -> tuple[str, list[str]]:
    """HTML -> GFM via BeautifulSoup normalisation + pandoc.

    * keeps only `selector` (default <main>, else <body>)
    * flattens table cells (<br>, <p>, colgroup, attributes) so pandoc emits pipe tables
    * rewrites in-page anchors that point at wrapper ids to the GFM slug of the section heading
    * absolutises relative links against base_url
    """
    from bs4 import BeautifulSoup  # local import: only needed for html sources

    warnings: list[str] = []
    soup = BeautifulSoup(text, "html.parser")
    root = soup.select_one(selector) if selector else (soup.find("main") or soup.body)
    if root is None:
        raise ValueError(f"selector {selector!r} matched nothing")
    for bad in root.find_all(["script", "style", "noscript", "iframe", "form", "button", "nav", "svg"]):
        bad.decompose()

    # anchor rewrite: id -> first heading slug inside that element
    id_to_slug = {}
    for el in root.find_all(id=True):
        h = el if re.match(r"^h[1-6]$", el.name or "") else el.find(re.compile(r"^h[1-6]$"))
        if h and h.get_text(strip=True):
            id_to_slug[el["id"]] = _slug(h.get_text(" ", strip=True))
    for a in root.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#") and href[1:] in id_to_slug:
            a["href"] = "#" + id_to_slug[href[1:]]
        elif not href.startswith(("#", "mailto:", "http://", "https://")):
            a["href"] = urljoin(base_url, href)
    for img in root.find_all("img", src=True):
        img["src"] = urljoin(base_url, img["src"])

    for t in root.find_all("table"):
        for cg in t.find_all("colgroup"):
            cg.decompose()
        for cell in t.find_all(["td", "th"]):
            for br in cell.find_all("br"):
                br.replace_with(" ")
            for blk in cell.find_all(["p", "div", "span"]):
                blk.unwrap()
            if cell.has_attr("rowspan") or cell.has_attr("colspan"):
                warnings.append("table with rowspan/colspan (pandoc may flatten it; review output)")
        for tag in [t, *t.find_all(True)]:
            tag.attrs = {k: v for k, v in tag.attrs.items() if k in ("rowspan", "colspan")}
    for d in root.find_all(["div", "section", "article", "span"]):
        d.unwrap()
    # attributes pandoc cannot express in Markdown (class, target, rel, data-*) force raw HTML output
    keep = {"href", "src", "alt", "title", "rowspan", "colspan"}
    for tag in root.find_all(True):
        tag.attrs = {k: v for k, v in tag.attrs.items() if k in keep}

    proc = subprocess.run(
        ["pandoc", "-f", "html", "-t", "gfm", "--wrap=none"],
        input=str(root), text=True, capture_output=True, check=True,
    )
    md = proc.stdout
    if "<table" in md:
        warnings.append("raw <table> left in output (complex table)")
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip() + "\n", sorted(set(warnings))


# --------------------------------------------------------------------------- yaml-dir
def convert_yaml_dir(docs: dict[str, str], title: str, columns: list[str]) -> tuple[str, list[str]]:
    """Render a directory of YAML records (e.g. a site's content collection) as Markdown:
    a summary table over `columns` followed by one section per record with every field."""
    import yaml

    warnings: list[str] = []
    recs = []
    for name, text in sorted(docs.items()):
        try:
            recs.append(yaml.safe_load(text) or {})
        except yaml.YAMLError as e:
            warnings.append(f"{name}: {e}")
    recs.sort(key=lambda r: (r.get("sortOrder", 1e9), str(r.get("id", ""))))

    def cell(v):
        if isinstance(v, dict):
            v = ", ".join(k for k, on in v.items() if on) if all(isinstance(x, bool) for x in v.values()) else json.dumps(v)
        elif isinstance(v, list):
            v = ", ".join(map(str, v))
        return str(v if v is not None else "").replace("|", "\\|").replace("\n", " ")

    out = [f"# {title}", "", "| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    out += ["| " + " | ".join(cell(r.get(c)) for c in columns) + " |" for r in recs]
    for r in recs:
        out += ["", f"## {r.get('displayName') or r.get('id')}", ""]
        for k, v in r.items():
            if isinstance(v, list):
                out.append(f"- **{k}:**")
                out += [f"  - {cell(x)}" for x in v]
            else:
                out.append(f"- **{k}:** {cell(v)}")
    return "\n".join(out) + "\n", warnings
