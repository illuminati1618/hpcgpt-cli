---
origin: kb
title: OpenCode primer — the parts hpcgpt-cli uses, with pointers into the upstream docs
author: Yash Parikh (illuminati1618)
updated: 2026-10-12
verified: docs-only
sources:
  - opencode-v1-config
  - opencode-v1-agents
  - opencode-v1-skills
  - opencode-v1-permissions
  - opencode-v1-tools
  - opencode-v1-custom-tools
  - opencode-v1-commands
  - opencode-v1-rules
  - opencode-v1-models
  - opencode-v1-providers
  - opencode-v1-mcp-servers
  - opencode-v1-plugins
  - opencode-v1-tui
  - opencode-v1-cli
  - opencode-v1-troubleshooting
  - hpcgpt-mkandes-notes
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). A reading map for OpenCode **V1** (what hpcgpt-cli targets). It explains only the concepts and links to the upstream docs (pinned copies: v1.18.32) for detail. For V2, see [v1-vs-v2.md](v1-vs-v2.md).

# OpenCode primer (V1)

OpenCode is an open-source terminal AI agent (the TUI plus a local HTTP server). It connects to any LLM provider,
exposes built-in tools (shell, file ops, web, skills) to the model, and is configured with JSON files and Markdown
definitions. hpcgpt-cli is purely a configuration of it ([architecture](../hpcgpt-cli/architecture.md)).

## Concepts → where to read

| Concept | One-liner | Upstream doc |
|---|---|---|
| Config files and precedence | JSON(C) files **merged** (later wins): remote → global → `OPENCODE_CONFIG` → project → `.opencode/` → `OPENCODE_CONFIG_CONTENT` → managed. `{env:X}` and `{file:path}` substitution | [config](https://opencode.ai/docs/config) |
| Agents | Primary agents (Tab to switch) and subagents (`@name` or `task` tool). JSON under `agent` or Markdown files (**filename = id**, body = system prompt). Frontmatter: `description`, `mode`, `model`, `temperature`, `permission` | [agents](https://opencode.ai/docs/agents) |
| Skills | `<name>/SKILL.md` under `.opencode/skills/`, `.claude/skills/` and `.agents/skills/` (searched from the working directory up to the git root), the same three under `~/` (`~/.config/opencode/skills/` for OpenCode), plus `skills.paths`; loaded on demand via the `skill` tool | [skills](https://opencode.ai/docs/skills), [authoring](skill-authoring.md) |
| Permissions | `allow` / `ask` / `deny` per tool key, with glob patterns for `bash`, `read`, `edit`, `skill`…; the last matching rule wins | [permissions](https://opencode.ai/docs/permissions) |
| Tools | Built-ins: `bash`, `read`, `edit`/`write`/`apply_patch`, `grep`, `glob`, `list`, `webfetch`, `websearch` (see below), `skill`, `task`, `todowrite`, `question`, `lsp` (experimental, off unless `OPENCODE_EXPERIMENTAL_LSP_TOOL=true`) | [tools](https://opencode.ai/docs/tools) |
| Custom tools | TS/JS functions in `tool(s)/` dirs | [custom-tools](https://opencode.ai/docs/custom-tools) |
| Providers and models | `provider.<id>` with `npm` (for example `@ai-sdk/openai-compatible`), `options.baseURL`/`apiKey`, `models.<api-id>.name` (label) and `limit` | [providers](https://opencode.ai/docs/providers), [models](https://opencode.ai/docs/models) |
| MCP servers | `mcp.<name>`: `type: local` (command) or `remote` (url); tools named `<name>_<tool>` | [mcp-servers](https://opencode.ai/docs/mcp-servers) |
| Commands | `/name` prompt templates (`command` config or `commands/*.md`) | [commands](https://opencode.ai/docs/commands) |
| Rules | `AGENTS.md` (project/global; `CLAUDE.md` as fallback) injected as instructions | [rules](https://opencode.ai/docs/rules) |
| Server plugins | JS/TS hooks (`tool.execute.before`, events), custom tools | [plugins](https://opencode.ai/docs/plugins) |
| TUI and TUI plugins | `tui.json(c)` via `OPENCODE_TUI_CONFIG`: theme, keybinds, `plugin` list | [tui](https://opencode.ai/docs/tui) |
| CLI | `opencode run`, `agent list`, `models`, `mcp list`, `debug config`, `serve`, `session`, `export` | [cli](https://opencode.ai/docs/cli) |
| Logs and storage | `~/.local/share/opencode/` (sessions, logs in `log/`) | [troubleshooting](https://opencode.ai/docs/troubleshooting) |

## Environment variables you'll actually use

| Var | Effect |
|---|---|
| `OPENCODE_CONFIG` | Extra config **file** (merged after global) |
| `OPENCODE_CONFIG_DIR` | Extra config **directory**, searched like `.opencode/` (agents, commands, plugins, skills). See [discovery](../hpcgpt-cli/architecture.md#config-discovery-the-thing-that-trips-people-up) |
| `OPENCODE_TUI_CONFIG` | TUI config file (theme, TUI plugins) |
| `OPENCODE_CONFIG_CONTENT` | Inline JSON config (highest non-managed precedence), useful for one-off tests |
| `OPENCODE_ENABLE_EXA=true` | Enables the `websearch` tool (Exa) with non-OpenCode providers such as Triton AI or NRP; `OPENCODE_ENABLE_PARALLEL` is the alternative backend. SDSC's [Expanse install notes](https://github.com/mkandes/notes/blob/main/2026/07/26.md) set it |
| `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` | Don't scan `.claude/skills` (`OPENCODE_DISABLE_CLAUDE_CODE=1` drops all `.claude` support, including `~/.claude/CLAUDE.md`) |
| `NRP_LLM_API_KEY`, `TRITON_AI_API_KEY` | Referenced by `SDSC/opencode.jsonc` as `{env:...}` |

## Everyday commands

```bash
opencode                                   # TUI in the current directory
opencode --agent hpcgpt -m nrp/qwen3       # pick agent and model
opencode run --agent hpcgpt "question"     # headless; add --format json for raw events
opencode debug config                      # print the merged config (check that your pack loaded)
opencode agent list                        # see which agents loaded (and their mode)
opencode models nrp                        # list models from a provider
opencode mcp list                          # MCP servers and status
```

Caveat: in the current pack, `--agent hpcgpt` selects a bare agent without the SDSC prompt or permissions, and the
persona is registered as `hpcGPT` ([known-issues A0](../hpcgpt-cli/known-issues.md)). `opencode agent list` shows both.

In the TUI: `/models`, `/sessions`, `/new`, `/undo`/`/redo`, `/compact`, `/details`, `/thinking`, `/export`, `/exit`
(`/share` is disabled by `"share": "disabled"` in `SDSC/opencode.jsonc`); **Tab** cycles primary agents. The SDSC TUI
plugins add `/jobs`, `/jobs-refresh` and `/feedback`, but only when `SDSC/tui.jsonc` is loaded (for example via
`OPENCODE_TUI_CONFIG`).
