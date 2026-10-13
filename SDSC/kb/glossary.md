---
origin: kb
title: Glossary
author: Yash Parikh (illuminati1618)
updated: 2026-10-12
verified: docs-only
sources:
  - nrp-aup
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). Short definitions with pointers. See also NRP's [glossary](https://nrp.ai/documentation/userdocs/start/glossary/).

# Glossary

| Term | Meaning | See |
|---|---|---|
| **ACCESS** | NSF program that allocates Expanse CPU/GPU time (successor of XSEDE) | [allocations](expanse/allocations-and-sus.md) |
| **Agent (OpenCode)** | A persona: prompt, model, and permissions. Primary (user-facing) or subagent | [primer](opencode/primer.md) |
| **Agent Skills / SKILL.md** | Open format for on-demand procedural knowledge; `name` + `description` always in context, body loaded when relevant | [skill-authoring](opencode/skill-authoring.md) |
| **AUP** | Acceptable Use Policy (NRP); non-commercial use only | [NRP AUP](https://nrp.ai/NRP-AUP.pdf) |
| **CILogon** | Federated login used by NRP (and SDSC services) | [NRP getting started](https://nrp.ai/documentation/userdocs/start/getting-started/) |
| **Compute capability (CC)** | NVIDIA architecture version: V100 = 7.0, A100 = 8.0, H100 = 9.0 | [gpu-selection](expanse/gpu-selection.md) |
| **Envoy AI Gateway** | NRP's LLM API gateway at `ellm.nrp-nautilus.io` | [llm-api](nautilus-nrp/llm-api-for-opencode.md) |
| **expanse-client** | SDSC CLI for allocation and usage queries (`module load sdsc`) | [allocations](expanse/allocations-and-sus.md) |
| **galyleo** | SDSC tool (by Marty Kandes) to launch Jupyter on Expanse through Slurm | [access](expanse/access-and-environment.md#jupyter) |
| **GPU SU** | 1 GPU-hour; the guide says with < 10 CPUs and < 92 GB (V100 nodes), but its examples use 10 cores / 96 GB. Exact boundary unverified | [allocations](expanse/allocations-and-sus.md) |
| **hpcGPT** | The multi-center OpenCode-based HPC support assistant; SDSC's pack is `SDSC` | [architecture](hpcgpt-cli/architecture.md) |
| **hpcGPT Chat / Illinois Chat** | RAG chat service (UIUC.chat stack) behind the `chat` MCP server; SDSC's instance is being deployed on Voyager | [architecture](hpcgpt-cli/architecture.md#mcp-server-sdscmcpchat-documentation-rag) |
| **Lmod / modules** | Environment modules system on Expanse (`module load gpu`) | [access](expanse/access-and-environment.md#modules-lmod) |
| **Lustre** | Expanse's parallel filesystem (`/expanse/lustre/...`); jobs need `--constraint=lustre` | [access](expanse/access-and-environment.md#storage) |
| **MCP** | Model Context Protocol: tools served to the agent by a separate process or server | [extending-skills](hpcgpt-cli/extending-skills.md) |
| **NAIRR** | National AI Research Resource Pilot; allocates Expanse's H100 nodes (`nairr-gpu*`) | [gpu-selection](expanse/gpu-selection.md) |
| **Namespace (NRP)** | Kubernetes namespace = NRP project/group; the LLM API requires membership in a group with the LLM flag | [overview](nautilus-nrp/overview.md) |
| **NRP / Nautilus** | National Research Platform; its Kubernetes cluster is called Nautilus | [overview](nautilus-nrp/overview.md) |
| **OpenCode V1 / V2** | `opencode-ai` 1.x (SDSC's target; docs here pinned at 1.18.32) vs `@opencode/cli` 2.x (new plugin API, `cli.json`) | [v1-vs-v2](opencode/v1-vs-v2.md) |
| **Partition** | Slurm queue: node type, sharing, limits and charging | [slurm-on-expanse](expanse/slurm-on-expanse.md) |
| **Project (Expanse)** | Linux group / Slurm account (`--account=abc123`), not the `TG-` grant id | [allocations](expanse/allocations-and-sus.md) |
| **SU** | Service Unit: 1 core-hour (≤ 2 GB) or 1 GPU-hour | [allocations](expanse/allocations-and-sus.md) |
| **TOTP / 2FA** | Required for Expanse password logins (enrol at passive.sdsc.edu) | [access](expanse/access-and-environment.md) |
| **Triton AI** | UCSD's LLM API (`tritonai-api.ucsd.edu`), the SDSC pack's current default provider | [llm-api](nautilus-nrp/llm-api-for-opencode.md#triton-ai-vs-nrp-current-sdsc-default-vs-alternative) |
| **TUI plugin** | OpenCode V1 terminal-UI extension (sidebar, slash commands); not compatible with V2 | [architecture](hpcgpt-cli/architecture.md#tui-plugins-v1-api) |
| **Voyager** | SDSC's AI system with a Kubernetes cluster; where SDSC's hpcGPT Chat backend is being deployed | [architecture](hpcgpt-cli/architecture.md) |
