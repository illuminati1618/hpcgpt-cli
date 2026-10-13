---
origin: kb
title: OpenCode V1 vs V2 — what it means for hpcgpt-cli
author: Yash Parikh (illuminati1618)
updated: 2026-10-12
verified: docs-only
sources:
  - opencode-v2-migrate-v1
  - opencode-v2-plugins-migrate-v1
  - opencode-v2-cli-plugins
  - opencode-v2-cli-config
  - opencode-v2-providers
  - opencode-v1-config
  - opencode-v2-skills
  - opencode-v1-19-0-release
  - opencode-npm-v1
  - opencode-npm-v2
  - opencode-v2-cli-plugins-build
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). Impact analysis of the V2 release on the SDSC pack. The authority is the upstream [Migrate from V1](https://opencode.ai/v2/docs/migrate-v1) guide (pinned copy: v2.0.18); versions and dates checked against npm and GitHub releases on 2026-10-12.

# OpenCode V1 vs V2: what it means for hpcgpt-cli

## Facts

| | V1 | V2 |
|---|---|---|
| npm package | `opencode-ai` | `@opencode/cli` (**2.0.0 released 2026-09-11**) |
| Latest at review (2026-10-12) | 1.19.0 (2026-10-11) | 2.0.27 (2026-10-12) |
| KB docs pinned at | v1.18.32 | v2.0.18 |
| Install | `curl -fsSL https://opencode.ai/install \| bash` or `npm i -g opencode-ai` | `curl -fsSL https://opencode.ai/v2/install \| bash` or `npm i -g @opencode/cli` |
| Binary | `opencode` | `opencode` (the same name; the V2 curl installer **replaces** V1; remove a package-managed V1 first) |
| Docs | <https://opencode.ai/docs> | <https://opencode.ai/v2/docs> |
| Git tags | `v1.x` | `v2.0.x` (the same repo, `anomalyco/opencode`) |

V2 has **three intentional breaking changes**: (1) a new plugin API, (2) new server API/client contracts, (3) terminal-client
config moves from layered `tui.json(c)` to a single global `~/.config/opencode/cli.json` (on first start, V2 migrates
the global `tui.json` only; project-local TUI config is not migrated). Everything else supported in V1 is meant to keep
working; if it doesn't, upstream treats it as a compatibility bug. Two smaller differences: V2 accepts `lsp` config but
runs no language servers, and it reads only `AGENTS.md` (no `CLAUDE.md` fallback).

## Impact on each SDSC file

| SDSC file | Under V2 | Action if/when SDSC moves |
|---|---|---|
| `opencode.jsonc` (V1 shape: `agent`, `provider`/`npm`/`options`, `mcp.<name>.enabled`, `snapshot`) | **Works**: V2 normalizes V1 fields in memory | Optional: convert to native V2 (`agents`, `providers`/`package`/`settings`, `mcp.servers` + `disabled`, `snapshots`, ordered `permissions` array). Keep each nested entry entirely in one format. |
| `agents/hpcgpt.md` | **Works** (legacy frontmatter is translated automatically) | Optional: `permission` → `permissions`; actions `bash` → `shell`, `write`/`patch` → `edit`; `temperature` moves under `request.body` |
| `skills/*/SKILL.md` | **Works unchanged** (V2 accepts `license`/`compatibility` but doesn't interpret them) | none |
| `tui.jsonc` (loaded via `OPENCODE_TUI_CONFIG`) | **Not read** by V2 (only a global `tui.json` is migrated, once, when `cli.json` is absent) | Move `theme`/`plugin` to `~/.config/opencode/cli.json` (`plugins`) |
| `plugins/slurm-sidebar`, `plugins/feedback` (V1 `TuiPluginModule`, `@opencode-ai/plugin/tui`) | **Do not run** ("V1 plugin implementations do not run in V2", [porting guide](https://opencode.ai/v2/docs/build/plugins/migrate-v1)) | Port to the V2 CLI plugin API: `Plugin.define({ setup(context) })` from `@opencode/plugin/tui`, slash commands in a keymap layer, the sidebar via a slot ([CLI plugins](https://opencode.ai/v2/docs/build/plugins/cli)); register in `cli.json` `plugins` |
| `mcp/chat` | **Works** (MCP protocol unchanged; config key normalized) | none |
| `module.lua` (still the NCSA Delta template: opencode 1.18.23, `OPENCODE_TUI_CONFIG`) | Package name and install URL differ; V2 docs don't mention `OPENCODE_TUI_CONFIG` (CLI settings come from the global `cli.json` or inline `OPENCODE_CLI_CONFIG_CONTENT`) | Pin one major version per module version |

**Don't mix within a deployment.** V1 and V2 share config locations. Pointing V1 at a config converted to V2-only
fields breaks V1. Since 1.19.0, V1 itself offers the jump: `opencode upgrade --major` upgrades to V2, and the TUI
`/update` command installs updates or upgrades to V2; updates are no longer installed automatically
([v1.19.0 release notes](https://github.com/anomalyco/opencode/releases/tag/v1.19.0)). V2 won't run the SDSC TUI
plugins. An unpinned `npm install -g opencode-ai` now installs 1.19.x.

## Recommendation

1. **Build and test skills against a pinned V1** (for example `npm i -g opencode-ai@1.18.32`, the version these docs
   are pinned to), since that's what the SDSC pack targets. Skills carry over to V2 unchanged.
2. **Don't write new TUI plugins against the V1 API** unless the SDSC maintainers ask for one. Put plugin-shaped ideas
   into a skill where possible.
3. The **NRP client-config recipe for OpenCode is written in the V2 shape** ([client configs](https://nrp.ai/documentation/userdocs/ai/llm-managed/client-configs/)).
   For V1, use the translated block in [../nautilus-nrp/llm-api-for-opencode.md](../nautilus-nrp/llm-api-for-opencode.md).
