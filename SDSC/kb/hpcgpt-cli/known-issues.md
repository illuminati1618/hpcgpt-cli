---
origin: kb
title: hpcgpt-cli SDSC — known issues and gaps
author: Yash Parikh (illuminati1618)
updated: 2026-10-12
verified: docs-only
sources:
  - opencode-v1-agents
  - opencode-v1-skills
  - opencode-v1-permissions
  - opencode-v1-providers
  - opencode-v1-models
  - expanse-user-guide
  - nrp-llm-lifecycle
  - nrp-llm-model-catalog
  - agentskills-specification
  - hpcgpt-mkandes-notes
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). Found by reading this repo at `6541176` and re-checked at `ff700b0` (latest `sdsc`, 2026-10-12), which changes only the model lists in `SDSC/opencode.jsonc`, so every reproduction below still applies.

# hpcgpt-cli SDSC: known issues and gaps

Sorted by impact on a researcher's session. Each item has a location, the symptom, and a suggested fix.

## A. Things that break or mislead at runtime

| # | Where | Problem | Fix |
|---|---|---|---|
| **A0** | `SDSC/agents/hpcgpt.md:2` + `SDSC/opencode.jsonc:10-12,15` | **[reproduced with opencode 1.18.7, 1.18.23 and 1.18.32]**: the version the SDSC Expanse install got ([note 2026-07-27](https://github.com/mkandes/notes/blob/main/2026/07/27.md?plain=1#L67)), the `module.lua` version, and the latest V1. Frontmatter `name: hpcGPT` makes OpenCode register the Markdown agent as **`hpcGPT`**, while `"agent": {"hpcgpt": {...}}` and `"default_agent": "hpcgpt"` create and select a **different, bare agent `hpcgpt`** (mode `all`). The agent users land in has **no SDSC prompt (0 chars), no temperature, and the default permissions `'*': allow`**, so `bash` and `edit` run **without asking**. The persona and `bash: ask`/`edit: deny` apply only if the user switches to `hpcGPT` by hand. `opencode agent list` shows both `hpcgpt (all)` and `hpcGPT (primary)`. | Delete the `name:` line from `hpcgpt.md` (verified: one `hpcgpt (primary)` agent with the 5632-char prompt, `bash: ask`, `edit: deny`). Reproduce with `OPENCODE_CONFIG_DIR=<pack copy> opencode agent list`. |
| A1 | `SDSC/mcp/chat/src/config.py:68-73` | **[reproduced]** `consolidate_config_and_args` checks `key.replace("_","-") in args`, but argparse stores `api_key` and `log_file`, not `api-key`/`log-file`. So **`config.json` always overrides `--api-key` and `--log-file`**, while `--url`, `--model`, `--host` and `--port` do override the file. This matches the [2026-09-09 note](https://github.com/mkandes/notes/blob/main/2026/09/09a.md) ("the `config.json` file values override any provided on the command-line"). | Compare `key` directly: `if getattr(args, key, None) is None: setattr(args, key, value)` |
| A2 | `SDSC/mcp/chat/src/config.py:55` | `DEFAULT_COURSES` is **never defined**. If `config.json` has no `courses` key, loading raises `NameError`. | Define `DEFAULT_COURSES = [{"name": "sdsctest-072326", "description": "..."}]` or make `courses` required. |
| A3 | `SDSC/mcp/chat/server.py:26,79,96` vs `SDSC/mcp/chat/README.md:13-16,94-97` | The README says one tool per `courses` entry (`query_<name>`), each verified at startup. The code **ignores `courses`**, registers one hard-coded tool, `query_docs`, against the test course `sdsctest-072326`, and verifies only that course. The README also gives a `timeout` default of 60 s (`README.md:79`); the code uses 120 (`config.py:52`). | Loop over `config.courses` and register a tool per course, as `NCSA/mcp_servers/illinois_chat_server/server.py:33-76` does; fix the README. |
| A4 | `SDSC/mcp/chat/src/config.py:39-47` | `json_schema_extra={"env": "HPCGPT_CHAT_URL"}` only adds JSON-schema metadata; a plain pydantic `BaseModel` never reads it, so the documented env vars `HPCGPT_CHAT_URL`/`_API_KEY`/`_MODEL` are ignored. | Use `pydantic-settings` `BaseSettings`, or read `os.environ` explicitly. |
| A5 | `SDSC/mcp/chat/server.py:41` | Tool calls use `requests.post(...)` **without a timeout** (only the startup check passes one, line 105), synchronously inside an `async def`. A slow chat backend blocks the MCP server's event loop, and OpenCode's tool call with it. | `timeout=self.timeout`, and `httpx.AsyncClient` or `asyncio.to_thread`. |
| A6 | `SDSC/mcp/chat/README.md:63` | Setup says `cp config.json config.json`, and no example config is committed (`config.json` is git-ignored by the root `.gitignore`). New users can't start the server. | Commit an `example.config.json`, like `NCSA/mcp_servers/*/example.config.json`. |
| A7 | `SDSC/skills/slurm/SKILL.md:191` | Tells the agent to use **`$SLURM_TMPDIR`**, a Digital Research Alliance of Canada convention. Expanse documents node-local scratch at **`/scratch/$USER/job_$SLURM_JOB_ID`** ([user guide: Local Scratch Disk](https://www.sdsc.edu/systems/expanse/user_guide.html)). | Replace, or add Expanse-specific text. Check whether `SLURM_TMPDIR` is set at all on Expanse ([checklist](../expanse/verify-on-expanse.md)). |
| A8 | `SDSC/skills/slurm/SKILL.md` | Generic Slurm only: no Expanse partitions, no `--account` requirement, no GPU partition rules, no `module reset` for GPU jobs. The agent must guess Expanse specifics. | Add Expanse references (a `references/` file in the skill), or a separate Expanse GPU skill (see [gpu-selection](../expanse/gpu-selection.md)). |
| A9 | `SDSC/prompts/support.txt:21-22,35,87` | (Unused, see B1.) Names tools that don't exist (`query_expanse_documentation`, `query_expanse_nairr_documentation`, `send_support_report`) and lists **"V100, A100, H100 GPUs"**. The user guide documents only V100 and H100 (NAIRR) partitions; a single undocumented A100 node exists ([gpu-selection](../expanse/gpu-selection.md)), so agents shouldn't offer A100s. | Delete, or rewrite if reused. |
| A10 | `SDSC/opencode.jsonc:16,20-56` | The `nrp` provider is defined but **not in `enabled_providers`**, so it can't be selected. Its model **keys** are NRP's aliases (`gemma`, `qwen3`, ...), which is correct: the key is the model id sent to the API and `name` is only a display label ([models](https://opencode.ai/docs/models)). The provider block doesn't set `limit.context`/`limit.output`, which OpenCode uses to know how much context is left ([providers](https://opencode.ai/docs/providers)). | Add `limit`s from the [catalog](https://nrp.ai/documentation/userdocs/ai/llm-managed/models/). Whether to add `"nrp"` to `enabled_providers` is SDSC's call. |

## B. Packaging and deployment gaps

| # | Where | Problem |
|---|---|---|
| B1 | `SDSC/prompts/*.txt` | Not referenced by `opencode.jsonc` (no `{file:./prompts/...}`), so they're dead files left over from the NCSA template. `report.txt` would need a `command.report` entry, as NCSA has (`NCSA/client-deployment/delta-opencode.jsonc:219-224`). |
| B2 | `SDSC/module.lua` | Still the **NCSA Delta** template: Delta help text and banner (lines 1-18, 31-40), `/sw/external/opencode` (line 2), `delta-opencode.jsonc` (line 22), `NCSA_LLM_URL` (line 24). It sets `OPENCODE_CONFIG` but not **`OPENCODE_CONFIG_DIR`**. With only `OPENCODE_CONFIG`, OpenCode loads no agent file and no skills, so users would get the bare `hpcgpt` agent even after A0 is fixed (see [architecture: config discovery](architecture.md#config-discovery-the-thing-that-trips-people-up)). |
| B3 | `SDSC/plugins/*/` | Plugin ids, command names and package names are still `ncsa-*` / `ncsa.*` (`slurm-sidebar/index.tsx:23,33,48`, `feedback/index.tsx:114,120`, both `package.json` files). Harmless alone, but they would collide if both the NCSA and SDSC plugins were loaded. |
| B4 | `SDSC/plugins/*` | **V1 TUI plugin API.** They won't load under OpenCode V2 (released 2026-09-11). See [../opencode/v1-vs-v2.md](../opencode/v1-vs-v2.md). |
| B5 | `SDSC/themes/sdsc.json` | Marked incomplete and unused (`tui.jsonc` uses `"theme": "system"`). |
| B6 | `SDSC/README.md` | Headings only, with no install or usage text, and there is no `SDSC/example.env` (the root `README.md` asks every center for one). [dev-workflow.md](dev-workflow.md) is the working substitute. |
| B7 | `SDSC/plugins/feedback/mail.js:9-16` | Needs a working `mail` binary and valid `HPCGPT_FEEDBACK_EMAIL` and `HPCGPT_FEEDBACK_FROM`, otherwise `/feedback` fails. Only the modulefile sets them, to `example.edu` placeholders (`SDSC/module.lua:25-26`). On Expanse, check that `mail` exists on login nodes. |

## C. Skill quality nits (cheap wins)

- `slurm/SKILL.md`: typos `premept` (line 194), `Gaurdrails` (line 202) and `commom` (line 213). "Common Problems" has
  one entry (OOM), linking to OSC docs. The `description` is generic, which can make it trigger too often or too
  rarely; see [skill-authoring](../opencode/skill-authoring.md#descriptions-decide-triggering).
- `expanse-client/SKILL.md`: typos `Availablity` (line 30) and `plain-formtted` (line 49). The body already says to
  run `module load sdsc` on `expanse-client: command not found` (lines 32-33); putting that failure mode in the
  `description` too would help the skill trigger when users paste the error.
- Both skills' `metadata.updated: 2026-07-30` (`slurm/SKILL.md:12`, `expanse-client/SKILL.md:19`) is an unquoted YAML
  **date**, but `metadata` must be a string→string map ([spec](https://agentskills.io/specification)). OpenCode 1.18.32
  only type-checks `name` and `description`, so the skills still load, but stricter validators may reject them. Fix:
  `updated: "2026-07-30"`.
- Neither skill uses `references/` or `scripts/` subfolders, which the spec allows and which keep `SKILL.md` short.
- Skill guardrails such as "never `sbatch` without confirmation" are **advisory**; the enforcement is the agent's
  `bash: ask`. For defense in depth, use granular bash permissions, as NCSA does in
  `NCSA/client-deployment/delta-opencode.jsonc`. The last matching rule wins, so `"*"` goes first:
  `"permission": {"bash": {"*": "ask", "squeue*": "allow", "sinfo*": "allow", "rm *": "deny"}}`.
