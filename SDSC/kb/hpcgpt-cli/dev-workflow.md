---
origin: kb
title: Dev workflow — running and testing the SDSC pack locally (WSL) and on Expanse
author: Yash Parikh (illuminati1618)
updated: 2026-10-12
verified: docs-only
sources:
  - opencode-v1-config
  - opencode-v1-cli
  - hpcgpt-mkandes-notes
  - nrp-llm-api-access
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). The local inspection commands (`opencode agent list`, `opencode debug skill|agent|config`, `opencode mcp list`, the `OPENCODE_CONFIG_CONTENT` overlay) were run on 2026-10-13 on Linux with opencode 1.18.32, dummy API keys and no LLM calls. The Expanse steps follow the SDSC setup notes of [2026-07-12](https://github.com/mkandes/notes/blob/main/2026/07/12.md) and [2026-07-26](https://github.com/mkandes/notes/blob/main/2026/07/26.md) and are **not verified end to end**; see [verify-on-expanse](../expanse/verify-on-expanse.md).

# Dev workflow

## 0. Get a working copy of the pack

OpenCode writes files into every config dir it loads (`.gitignore`, and `package.json`, `package-lock.json` and
`node_modules/` once a session starts), so run it against a **copy** of `SDSC/` rather than your checkout:

```bash
git clone https://github.com/mkandes/hpcgpt-cli.git && cd hpcgpt-cli && git switch sdsc
# refresh the copy (re-run after every edit or pull):
rsync -a --delete --exclude kb/ --exclude node_modules/ SDSC/ ~/.cache/sdsc-pack/
sed -i '/^name: hpcGPT$/d' ~/.cache/sdsc-pack/agents/hpcgpt.md   # agent-name fix, until A0 is fixed on sdsc
```

The `sed` line applies the [A0](known-issues.md) fix to the copy. Without it, the default agent `hpcgpt` has no SDSC
prompt and `'*': allow`, so it runs shell commands **without asking**. The rest of this page assumes the fix.

To change settings without editing the copy (an `rsync` would overwrite your edits), use `OPENCODE_CONFIG_CONTENT`. It
is merged after `OPENCODE_CONFIG_DIR`, so it wins. A file passed with `OPENCODE_CONFIG` does **not** work here: it is
merged before the config dir, and the pack's `opencode.jsonc` overrides it. For example, to switch to NRP and turn off
the `chat` MCP server:

```bash
export OPENCODE_CONFIG_CONTENT='{"enabled_providers":["triton-ai","nrp"],"model":"nrp/qwen3",
  "agent":{"hpcgpt":{"model":"nrp/qwen3"}},"mcp":{"chat":{"enabled":false}}}'
```

The `agent.hpcgpt.model` entry is needed because `agents/hpcgpt.md` pins its own `model:`. See
[NRP for OpenCode](../nautilus-nrp/llm-api-for-opencode.md) for model choices.

## 1. Local (WSL/Linux laptop): fast iteration, no Slurm

```bash
export OPENCODE_CONFIG_DIR=~/.cache/sdsc-pack
export OPENCODE_TUI_CONFIG=~/.cache/sdsc-pack/tui.jsonc

# static inspection (no LLM calls; dummy API keys are fine)
opencode agent list              # expect hpcgpt (primary) plus the hidden built-ins
opencode debug skill             # expect slurm, expanse-client, any skill you added, and the built-in customize-opencode
opencode debug agent hpcgpt      # prompt, permissions, model
opencode mcp list                # chat shows "failed" unless the chat MCP server is running

# real session (default provider is Triton AI)
export TRITON_AI_API_KEY=...     # or NRP_LLM_API_KEY from https://nrp.ai/llmtoken with the overlay above; never commit keys
opencode
opencode run --agent hpcgpt "which GPU should I use to fine-tune a 7B model with LoRA on Expanse?"
```

To keep your own `~/.config/opencode` out of the picture, point `HOME` (or `XDG_CONFIG_HOME`, `XDG_DATA_HOME`,
`XDG_CACHE_HOME`, `XDG_STATE_HOME`) at a scratch directory for the session.

Locally, `squeue` and `expanse-client` don't exist. That's enough to test that the agent *proposes* the right commands
and asks before running them, but not to check their output.

## 2. On Expanse: the real environment

```bash
ssh <user>@login.expanse.sdsc.edu
# OpenCode V1 in $HOME. npm may block install scripts; allow opencode's:
module load nodejs 2>/dev/null || true             # check the module name with: module spider node
npm config set allow-scripts=opencode-ai --location=user
npm install -g opencode-ai@1.18.32                  # or: curl -fsSL https://opencode.ai/install | bash
opencode --version

# get the pack copy as in step 0 (clone + rsync + sed), or rsync your local copy up
export OPENCODE_CONFIG_DIR=~/.cache/sdsc-pack OPENCODE_TUI_CONFIG=~/.cache/sdsc-pack/tui.jsonc
export TRITON_AI_API_KEY=...      # never commit; the 2026-07-12 note's TRITONAI_API_KEY is not the name the config reads
export OPENCODE_ENABLE_EXA=true   # enables websearch
opencode
```

Notes:

- The 2026-07-26 setup copies `opencode.jsonc`, `agents/` and `skills/` into `~/.config/opencode/`. If you did that,
  **remove the copies** before using `OPENCODE_CONFIG_DIR`. Otherwise both sets load: same-named skills log a
  duplicate warning, and anything you deleted from the pack still loads from the old copy. Full reset (from the setup
  notes): `rm -rf ~/.bun ~/.cache/opencode ~/.config/opencode ~/.local/share/opencode ~/.local/state/opencode`.
- Anything heavy the agent proposes belongs in a job
  ([access-and-environment](../expanse/access-and-environment.md#login-nodes-whats-allowed)).
- The `chat` MCP server needs its backend and a tunnel ([architecture](architecture.md#mcp-server-sdscmcpchat-documentation-rag)).
  For skill work, disable it with the overlay in step 0.

## 3. What to check for each skill change

1. `opencode debug skill` lists it. This only proves the frontmatter parsed and has a string `name`: 1.18.32 does
   **not** enforce the naming rules, so also check that `name` matches the directory and
   `^[a-z0-9]+(-[a-z0-9]+)*$` yourself ([extending-skills](extending-skills.md#2-where-it-lives-and-how-its-registered)).
2. Trigger tests (about 10 prompts that should trigger it and 10 that shouldn't) via `opencode run --format json`
   ([recipe](extending-skills.md#scripted-trigger-tests-cheap-evals)).
3. On Expanse: one real interactive request end to end (`gpu-debug`, 5 minutes), with the transcript saved.
4. For comparisons (with vs without a skill, generic vs site-specific), follow
   [skill-evaluation-metrics](../evaluation/skill-evaluation-metrics.md).
