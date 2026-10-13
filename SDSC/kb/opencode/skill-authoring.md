---
origin: kb
title: Writing good skills for hpcGPT (Agent Skills + OpenCode specifics)
author: Yash Parikh (illuminati1618)
updated: 2026-10-12
verified: docs-only
sources:
  - agentskills-specification
  - agentskills-best-practices
  - agentskills-optimizing-descriptions
  - agentskills-evaluating-skills
  - agentskills-using-scripts
  - opencode-v1-skills
  - hpcgpt-anthropic-skills
  - hpcgpt-skills-best-practices
  - hpcgpt-slurm-skill-imperial
  - hpcgpt-slurm-skill-rizvi
  - hpcgpt-mkandes-notes
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). A condensed checklist distilled from the [Agent Skills docs](https://agentskills.io/specification), plus what's specific to OpenCode (V1) and to HPC support. For *where* skills go in hpcgpt-cli, see [../hpcgpt-cli/extending-skills.md](../hpcgpt-cli/extending-skills.md).

# Writing good skills for hpcGPT

## Format

**Follow the layout of the existing SDSC skills** ([extending-skills § 3](../hpcgpt-cli/extending-skills.md#3-sdsc-conventions-from-the-existing-skills)).

| Rule | Kind | Source |
|---|---|---|
| `skills/<name>/SKILL.md`; `name` == directory name; `^[a-z0-9]+(-[a-z0-9]+)*$`, 1–64 chars (OpenCode 1.18.32 does **not** enforce this: a bad name still loads, so check it yourself) | required | [spec](https://agentskills.io/specification), [OpenCode](https://opencode.ai/docs/skills) |
| `description` required, non-empty, **≤ 1024 chars** | required | [spec](https://agentskills.io/specification), [OpenCode](https://opencode.ai/docs/skills) |
| OpenCode recognizes only `name`, `description`, `license`, `compatibility`, `metadata` (string→string) and ignores other fields. The spec's `allowed-tools` (experimental) is therefore **ignored by OpenCode**: use agent `permission` instead | OpenCode behavior | [OpenCode](https://opencode.ai/docs/skills) |
| `compatibility` ≤ 500 chars | required (if used) | [spec](https://agentskills.io/specification) |
| Body < 5000 tokens and **< 500 lines**. Move detail to `references/`, keep references **one level deep**, use relative paths from the skill root | recommended | [spec: progressive disclosure](https://agentskills.io/specification#progressive-disclosure) |
| Optional dirs: `scripts/` (executables), `references/` (docs loaded on demand), `assets/` (templates) | convention | [spec](https://agentskills.io/specification) |

## How loading works (and why the description matters most)

1. At startup only `name` and `description` of every skill are in context (~100 tokens each, listed in the `skill` tool's description).
2. When the task matches, the model calls the `skill` tool and the full `SKILL.md` body is injected.
3. Files in `references/` and `scripts/` are read or run only if the body tells the model to.

Agents consult skills mainly for tasks **beyond what they can do alone** ([optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions)).
"What's `ls -la`?" won't load a skill. "Get me a GPU debug node on Expanse" should.

### Descriptions decide triggering

From [optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions):

- **Imperative**: "Use this skill when…", not "This skill does…".
- **User intent, not implementation**: phrase it the way users do ("I need a GPU", "my job is stuck pending"), not
  the way the tool works ("wraps srun").
- **Be pushy**: list the contexts it applies to even when the user doesn't name the domain ("…even if they don't
  mention Slurm or partitions").
- **Concise**: a few sentences.

For example, the SDSC `slurm` skill's description ("Use the Slurm Workload Manager, write batch job scripts, debug common job submission…",
`SDSC/skills/slurm/SKILL.md:3-7`) is broad and uses tool vocabulary. A trigger-oriented rewrite for an Expanse GPU skill would look like:

```yaml
description: >
  Use this skill whenever an Expanse user wants to get onto a GPU, whether for an
  interactive/debug session, a batch training job, or advice on which GPU (V100 vs
  H100) and how many CPUs/memory to request, even if they don't mention Slurm,
  partitions, srun or sbatch. Also use it when a GPU job is pending, over-charged,
  out of memory, or fails with bf16/FlashAttention errors on V100.
```

## Content (what makes HPC skills good)

From [best practices](https://agentskills.io/skill-creation/best-practices), applied to Expanse:

- **Add what the model lacks; skip what it knows.** Models already know generic Slurm. They don't know that Expanse needs
  `--account`, that `gpu-debug` caps at 2 GPUs and 30 min, that a GPU job defaults to 1 CPU + 1 GB, that NAIRR needs
  `--gpus=h100:N`, or that Lustre needs `--constraint=lustre`. **Put Expanse-specific facts and gotchas first.**
- **Provide defaults, not menus.** "Default: `gpu-debug`, `--gpus=1 --ntasks-per-node=10 --mem=92G -t 00:30:00`" beats
  listing every flag.
- **Procedures over declarations.** Numbered steps: *1. find project with `expanse-client` → 2. check `sinfo` →
  3. propose command → 4. wait for confirmation → 5. run → 6. verify with `nvidia-smi`.*
- **Gotchas section.** This is the highest-value part of a skill. Collect gotchas from real tickets and
  [known issues](../hpcgpt-cli/known-issues.md).
- **Templates for output**: fixed script skeletons in `assets/` (for example `assets/gpu-shared.sb`).
- **Validation loops**: `bash -n job.sb` → `sbatch --test-only job.sb` (validates without submitting) → ask the user → `sbatch`.
- **Match control to fragility.** Be strict and exact where a mistake costs SUs (exclusive partitions, `--gpus=4`), and
  give latitude elsewhere.
- **Real output.** The SDSC `expanse-client` skill embeds real command output captured on Expanse. Capture yours per [verify-on-expanse](../expanse/verify-on-expanse.md), and redact usernames and project codes.

## Scripts in skills

From [using scripts](https://agentskills.io/skill-creation/using-scripts). On Expanse, scripts run **as the user on a
login node**, through the agent's `bash` permission (`ask` in `SDSC/agents/hpcgpt.md`), so:

- Read-only helpers (parse `expanse-client` into JSON, summarize `sacct`) are ideal.
- No interactive prompts. Support `--help`. Write clear errors and structured output (TSV/JSON, not aligned columns).
- Never let a script call `sbatch`/`srun`/`scancel` itself. The model proposes the command and the user approves it.
- Scripts must be cheap on login nodes: no loops over `sacct` for thousands of jobs, no heavy Python imports.

## Evaluate

From [evaluating skills](https://agentskills.io/skill-creation/evaluating-skills):

- **Triggering**: about 20 labelled prompts (8–10 should trigger, 8–10 shouldn't), each run several times because
  triggering is nondeterministic, with `opencode run --agent <agent> --format json`
  ([recipe](../hpcgpt-cli/extending-skills.md#scripted-trigger-tests-cheap-evals)). Test the agent users actually land
  in; see [known-issues A0](../hpcgpt-cli/known-issues.md) for why `hpcgpt` and `hpcGPT` currently differ.
- **Quality**: fixed tasks with checkable properties, for example "partition is `gpu-debug`", "has `--account`",
  "`--mem` set", "no `sbatch` without confirmation". Compare against a run with the skill denied.
- Re-run after changing the description, the default model, or the OpenCode version.

## Prior art to borrow from

- Prior art listed in SDSC's [Expanse deployment notes](https://github.com/mkandes/notes/blob/main/2026/07/26.md):
  [mgechev/skills-best-practices](https://github.com/mgechev/skills-best-practices) and two community Slurm skills
  ([Imperial College](https://github.com/ImperialCollegeLondon/ese-borg-skills/blob/main/plugins/slurm/skills/slurm/SKILL.md),
  [michaelrizvi](https://github.com/michaelrizvi/claude-config/blob/main/skills/slurm/SKILL.md)). Also
  [anthropics/skills](https://github.com/anthropics/skills) for well-structured examples.
- NCSA's `debug.txt`/`learning.txt` prompts (in `NCSA/client-deployment/prompts/`) contain well-tested HPC
  etiquette rules (login node vs Slurm) that can be adapted into skill gotchas.
