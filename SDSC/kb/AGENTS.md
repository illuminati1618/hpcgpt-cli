# AGENTS.md — rules for agents editing the SDSC knowledge base

Scope: `SDSC/kb/` only. This folder documents the SDSC hpcGPT pack, Expanse, the NRP LLM API, OpenCode skills, and
skill evaluation. Start at [README.md](README.md).

## Rules

1. **Link, don't copy.** Never paste upstream documentation into a doc. Link the upstream page, or quote a line or two
   with a citation. Docs hold only SDSC synthesis: how things fit together, Expanse specifics, analysis of this repo.
2. **Register every source.** Any page you relied on gets a `[[source]]` entry in
   [`sources/registry.toml`](sources/registry.toml) with a `note` saying what it was used for (one line). Use
   `mode = "link"` unless an offline copy is worth having. Cite the ids in the doc's `sources:` frontmatter.
3. **Mirrors are local only.** `tools/ingest.py` writes copies of mirrored sources into `sources/<group>/` (plus
   `INDEX.md` and `lock.json`). They are gitignored: never commit them, and never link to them from a doc. Link the
   upstream URL instead.
4. **Never write secrets.** API keys (`NRP_LLM_API_KEY`, `TRITON_AI_API_KEY`, ...) go in environment variables or
   untracked files. Redact usernames, project codes and job IDs that aren't already public.
5. **Cite code by path and line** from the repo root, for example `SDSC/agents/hpcgpt.md:7`.
6. Run `python3 SDSC/kb/tools/check.py` before committing. It must report 0 errors.

## Doc format

Every doc except `README.md` and `AGENTS.md` starts like this:

```markdown
---
origin: kb
title: "Short title"
author: Your Name (github-handle)
updated: 2026-10-12
verified: docs-only
sources:
  - expanse-user-guide
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). One line on scope and how it was checked.
```

`author` is whoever wrote the doc (add yourself, comma-separated, when you substantially revise one). Linked
upstream sources keep their own authors and never get an `author` line.

`verified` values:
- `docs-only`: derived from documentation or code reading; not yet run on a real system.
- `expanse-YYYY-MM-DD`: commands and outputs checked on Expanse on that date.
- `nrp-YYYY-MM-DD`: checked against the live NRP API on that date.

Anything `docs-only` that a user or skill would act on goes on
[expanse/verify-on-expanse.md](expanse/verify-on-expanse.md).

## Facts agents get wrong (check here first)

- **Expanse has no H200s.** GPU partitions are `gpu`/`gpu-shared`/`gpu-debug`/`gpu-preempt` (4× V100-32GB per
  node) and `nairr-gpu`/`nairr-gpu-shared` (4× H100 per node, NAIRR allocations only, **no Lustre**). See
  [expanse/gpu-selection.md](expanse/gpu-selection.md).
- **OpenCode has two major versions.** The SDSC pack targets **V1** (`opencode-ai` 1.x; `module.lua` pins 1.18.23). **V2**
  (`@opencode/cli` 2.x, released 2026-09-11) still reads V1 config, agents and skills, but V1 plugins do not run in it.
  See [opencode/v1-vs-v2.md](opencode/v1-vs-v2.md).
- `OPENCODE_CONFIG` only adds a config *file*. Agents and skills are discovered from `~/.config/opencode/`,
  `.opencode/`, or `OPENCODE_CONFIG_DIR` (skills also from `.claude/skills/` and `.agents/skills/`). See
  [hpcgpt-cli/architecture.md](hpcgpt-cli/architecture.md).
