# SDSC knowledge base for hpcgpt-cli

Written and maintained by Yash Parikh ([@illuminati1618](https://github.com/illuminati1618)). Linked upstream sources
are the work of their own authors (see [`sources/registry.toml`](sources/registry.toml)).

Notes for building and supporting the hpcGPT agent on **Expanse**: how the SDSC OpenCode pack works,
Expanse facts that skills depend on, the NRP LLM API, OpenCode skill authoring, and how to evaluate skills.

- This folder is documentation only. OpenCode never loads it (it reads `agents/`, `skills/`, `plugins/` and the config
  files of `SDSC/`), and a deployment of the pack can leave `kb/` out.
- Everything here is our own synthesis. Upstream docs are **linked, not copied**; every source we relied on is listed
  with a one-line reason in [`sources/registry.toml`](sources/registry.toml).
- Agents working in this folder: read [AGENTS.md](AGENTS.md) first.

## Start here, by task

| I want to... | Read |
|---|---|
| understand what hpcgpt-cli is and how a session works | [hpcgpt-cli/architecture](hpcgpt-cli/architecture.md) |
| add a skill (or agent, plugin, MCP tool) | [hpcgpt-cli/extending-skills](hpcgpt-cli/extending-skills.md) → [opencode/skill-authoring](opencode/skill-authoring.md) |
| run and test the SDSC pack (WSL or Expanse) | [hpcgpt-cli/dev-workflow](hpcgpt-cli/dev-workflow.md) |
| know what's broken in the SDSC pack | [hpcgpt-cli/known-issues](hpcgpt-cli/known-issues.md) (**A0**: the default agent has no guardrails) |
| help a researcher get a GPU | [expanse/gpu-selection](expanse/gpu-selection.md) |
| write Slurm commands and scripts for Expanse | [expanse/slurm-on-expanse](expanse/slurm-on-expanse.md) |
| explain SUs and allocations and read `expanse-client` | [expanse/allocations-and-sus](expanse/allocations-and-sus.md) |
| log in, and learn login-node rules, modules and storage | [expanse/access-and-environment](expanse/access-and-environment.md) |
| measure whether a skill works (tokens, consistency, generic vs Expanse) | [evaluation/skill-evaluation-metrics](evaluation/skill-evaluation-metrics.md) |
| the Study 1 design: no skill vs generic vs Expanse skill (arms, questions, primary comparison) | [evaluation/study-1-protocol](evaluation/study-1-protocol.md) |
| know which claims still need a live Expanse check | [expanse/verify-on-expanse](expanse/verify-on-expanse.md) |
| use NRP's free LLM API from OpenCode | [nautilus-nrp/llm-api-for-opencode](nautilus-nrp/llm-api-for-opencode.md) |
| understand NRP/Nautilus in general | [nautilus-nrp/overview](nautilus-nrp/overview.md) |
| learn OpenCode concepts fast | [opencode/primer](opencode/primer.md) |
| decide about OpenCode V2 | [opencode/v1-vs-v2](opencode/v1-vs-v2.md) |
| look up a term | [glossary](glossary.md) |

## Layout

```text
SDSC/kb/
  hpcgpt-cli/   architecture · extending-skills · dev-workflow · known-issues
  expanse/      access-and-environment · slurm-on-expanse · gpu-selection · allocations-and-sus · verify-on-expanse
  nautilus-nrp/ overview · llm-api-for-opencode
  opencode/     primer · skill-authoring · v1-vs-v2
  evaluation/   skill-evaluation-metrics, study-1-protocol, study-1/ (study.toml, questions.toml)
  glossary.md
  sources/      registry.toml (every source + why) · README.md · local mirrors (generated, gitignored)
  tools/        ingest.py (mirror sources locally) · check.py (lint) · convert.py
```

## Offline copies of the sources

```bash
pip install -r SDSC/kb/tools/requirements.txt     # also needs pandoc on PATH
python3 SDSC/kb/tools/ingest.py                   # writes SDSC/kb/sources/<group>/*.md (gitignored)
python3 SDSC/kb/tools/check.py                    # lint: frontmatter, source ids, links
```

## Conventions

Each doc has frontmatter (`origin: kb`, `title`, `updated`, `verified`, and `sources:` = registry ids) and starts with
the `SDSC KB DOC` banner. `verified: docs-only` means it hasn't been checked against a live system yet; claims an agent
would act on are listed in [verify-on-expanse](expanse/verify-on-expanse.md). Details: [AGENTS.md](AGENTS.md).
