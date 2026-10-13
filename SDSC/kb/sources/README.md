# sources/ — the list of upstream docs the KB relies on

[`registry.toml`](registry.toml) lists every external page the KB docs and SDSC skills relied on, with a one-line
`note` on why. Docs cite these ids in their `sources:` frontmatter. `tools/ingest.py` can also download **local,
offline copies** (mirrors) so agents can grep them; those copies are gitignored and never committed, because most
upstream pages are someone else's work and several declare no license.

| File | Written by | Committed? | Purpose |
|---|---|---|---|
| [`registry.toml`](registry.toml) | **humans** | yes | What each source is, where from, why we used it; what to mirror vs only link |
| `lock.json` | ingest.py | no | Resolved commit SHA, content hash, converter fingerprint, retrieval date per source |
| `INDEX.md` | ingest.py | no | Catalogue of every source (mirrored + link-only) |
| `<group>/<id>.md` | ingest.py | no | The local copy, with provenance frontmatter + banner |

## Workflow

```bash
cd SDSC/kb
pip install -r tools/requirements.txt        # bs4, PyYAML; also needs pandoc on PATH
python3 tools/ingest.py                      # refresh every local copy (idempotent; ~30 s)
python3 tools/ingest.py --group nrp          # one group
python3 tools/ingest.py --only expanse-user-guide
python3 tools/ingest.py --check              # what changed upstream? writes nothing
python3 tools/check.py                       # frontmatter + source id + link lint (run before committing)
```

**Adding a source:** append a `[[source]]` block to `registry.toml`, run `ingest.py --only <id>`, and read the
output. If the converter printed `warn` lines, check the result by hand. Commit only `registry.toml`.

**Choosing a source, best first:**
1. Raw Markdown/MDX from the repo that builds the site. Examples: `anomalyco/opencode` for opencode.ai, `prp/nrp-site` for nrp.ai.
2. The site's own `.md` endpoint or `llms.txt`. Example: agentskills.io serves `<page>.md`.
3. The rendered HTML page, converted with pandoc. Example: sdsc.edu, which has no public source repo.
4. `mode = "link"` when the page is huge, versioned by installation (Slurm man pages), binary (PDF), or a personal notebook (e.g. `mkandes/notes`).

Pin a **tag** when the docs describe a versioned product (opencode V1 → `v1.18.32`, V2 → `v2.0.18`).
Track a **branch** for living sites. The commit SHA is still recorded in `lock.json` and in each file's `ref:`.

## Provenance format (every mirrored file)

```markdown
---
origin: external                 # vs `kb` in docs and `generated` for INDEX.md
source_id: opencode-v1-skills
title: "Agent Skills (SKILL.md discovery + frontmatter rules)"
source_url: https://opencode.ai/docs/skills       # human page: cite this
fetched_from: https://raw.githubusercontent.com/anomalyco/opencode/<sha>/packages/web/src/content/docs/skills.mdx
ref: "v1.18.32 @ 0123456789ab"
retrieved: 2026-09-27
status: auto                     # or fixed
license: "MIT"
---

> **EXTERNAL SOURCE (mirrored, not written by us).** Upstream: <...> ...
```

`tools/check.py` checks any local copies it finds for this header, and checks every doc for the `origin: kb` header.

## Converters (`tools/convert.py`)

| format | How | Known limits |
|---|---|---|
| `md` | Strip upstream frontmatter (title/description become a heading); make root-relative links absolute | none |
| `mdx` | Fence-aware normaliser for Astro/Starlight: drops `import`/`export` outside code fences; `:::note`, `<Aside>` and `<Callout>` become blockquotes; `<TabItem>` becomes a bold label; `<ConfigDrawer>` becomes a labelled block; `<LinkButton>` and `<LinkCard>` become links; inline `<Badge text=X/>` becomes `**[X]**` | Data-driven widgets (`<ModelFeatureMatrix>`) have no content in the source, so a placeholder note is left and the underlying data is mirrored separately (see `nrp-llm-model-catalog`) |
| `html` | BeautifulSoup keeps `selector`, flattens table cells, removes non-Markdown attributes, and rewrites wrapper-id anchors to heading slugs; then `pandoc -t gfm` | `colspan` section rows are flattened into the first column, which still reads correctly |
| `yaml-dir` | Renders a directory of YAML records as a summary table plus one section per record | none |

The lock stores a **converter fingerprint** (a hash of `convert.py`). Improving a converter re-renders every
`auto` source on the next run, even when upstream hasn't changed.

## When a conversion is wrong

Fix the converter (`tools/convert.py`) so every page benefits, and add a case to `tools/test_convert.py`.
Hand-edited copies (`status = "fixed"`) are not used here: copies are local and regenerated, so a hand fix would
not reach anyone else.

## Licensing

opencode docs are MIT and agentskills.io is Apache-2.0. The SDSC training repos, `mkandes/batch-computing`, the
nrp.ai site and sdsc.edu pages declare no license. That is why this repository publishes only links and our own
synthesis, and keeps the downloaded copies out of git.
