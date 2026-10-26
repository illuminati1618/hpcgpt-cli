---
origin: kb
title: "Study 1 protocol: no skill vs generic skill vs Expanse skill"
author: Yash Parikh (illuminati1618)
updated: 2026-10-26
verified: docs-only
sources:
  - opencode-v1-permissions
  - opencode-v1-cli
  - opencode-v1-agents
  - evals-anthropic-statistical
  - evals-anthropic-demystifying
  - evals-skillsbench
  - agentskills-evaluating-skills
  - expanse-user-guide
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). Pre-registered design for the first skill study, written before any study runs. The harness was smoke-tested on a laptop and in a container on 2026-10-26; no Expanse runs yet. Background and metric choices: [skill-evaluation-metrics](skill-evaluation-metrics.md).

# Study 1 protocol: no skill vs generic skill vs Expanse skill

**Question.** For the two skill areas that have both a generic and an Expanse-specific version (environment
modules and conda), is the generic skill good enough, or does the Expanse version earn its keep? And does
either beat no skill?

**Hypothesis.** The generic skill is good enough: it solves about as many tasks as the Expanse skill at
about the same token cost.

**Status.** Pilot. 5 questions are enough to test the harness and measure variance, not to settle the
question. The pilot's job is to fix the task count and repeat count for the full study
([staged plan](skill-evaluation-metrics.md#a-paired-pre-registered-design-in-stages), stage 3).

## Arms

Every arm is the SDSC pack (`SDSC/` at the pinned `base_ref`) with the same agent, model, prompt and bash policy.
Only `skills/` differs.

| Arm | Skills added | Pinned commits |
|---|---|---|
| **A** no skill | none | n/a |
| **B** generic | `hpc-modules`, `hpc-conda` | heads of `skill/hpc-modules`, `skill/hpc-conda` |
| **C** Expanse | `expanse-modules`, `expanse-conda` | heads of `skill/expanse-modules`, `skill/expanse-conda` |

All arms keep the two shipped skills that have no twin (`slurm`, `expanse-client`) and OpenCode's built-in
`customize-opencode`. Exact SHAs are in [study-1/study.toml](study-1/study.toml) and are recorded in every
run's `meta.json`. The B and C skills have the same structure, step count and author, so the comparison
isolates specificity.

**Arms are built by leaving skill directories out**, not with `permission.skill` deny rules: a denied skill's
description may still be listed, and the agent sets `skill: allow`. Each arm is checked before any run with
`skilleval.py check-arms --probe`, which lists the discovered skills and sends "Reply with just OK." On
2026-10-26 the probe gave input tokens A 7,528, B 7,975 (+447), C 7,947 (+419): the cost of listing the two
extra skill descriptions, paid on every request.

## Fixed conditions

| | Value | Why |
|---|---|---|
| Model | `nrp/gemma` (Gemma 4 31B on the NRP LLM service) | The current baseline model for the SDSC pack. The production agent file names `triton-ai/api-gemma-4-31b`, the same model family on different hardware |
| OpenCode | 1.18.32 (V1) | Latest V1; the harness refuses to run on another version |
| Agent | `hpcGPT` (`--agent hpcGPT`) | `SDSC/agents/hpcgpt.md` registers as `hpcGPT`; the config's `default_agent: hpcgpt` selects a bare agent without the SDSC prompt ([known-issues A0](../hpcgpt-cli/known-issues.md)). Reproduced on 2026-10-26: a run without `--agent` used `hpcgpt (all)` |
| Temperature | 0.1 | From the agent file |
| Start state | empty working directory; user's own HOME (Expanse) or the container's (rehearsal) | Same for all arms within an environment |
| Run order | all (question, arm, repeat) triples shuffled with a fixed seed | So NRP throttling and time of day don't bias one arm |
| Repeats | 3 per question per arm | 45 runs for the pilot |

### Bash policy

The agent file sets `bash: ask`. **Headless `opencode run` auto-rejects every `ask`** (2026-10-26:
`permission requested: bash (...); auto-rejecting`), so under the production setting the skills' discovery
steps never run. For the study the harness replaces `bash: ask` with a **read-only allowlist** in the arm's
copy of the agent file ([study.toml `[permission.bash]`](study-1/study.toml)):

- catch-all `"*": deny`, then allow for read-only commands: `module`, `source`, `ls`, `cat`, `grep`, `awk`,
  `df`, `du`, `conda info|env list|list|config --show`, `sinfo`, `squeue`, `sacct`, `scontrol show`,
  `expanse-client`, `lfs quota`, and shell builtins the skills use;
- specific denies last (OpenCode applies the last matching rule): `> file`, `>>`, `tee`, `sed -i`,
  `find -delete|-exec`, `module save`;
- `external_directory: allow`, so the agent can read outside its empty working directory.

Checked on 2026-10-26 by asking the agent to run 16 commands verbatim. Allowed and ran: compound commands,
`for` loops, and the step-1 audits of `hpc-modules`, `hpc-conda` and `expanse-conda`. Denied, and no files
were created: `rm`, `touch`, `> file`, `| tee`, `sed -i`, `X=1 rm ...`, `C=...; touch "$C"`, `$(touch ...)`.
OpenCode checks each sub-command, including ones inside `$(...)`.

This differs from production in one way that matters: in production a human answers each prompt. The
allowlist approximates "the user approves read-only commands and refuses writes". The skills' guardrails
already say read-only, so a skill that needs a write to succeed is a finding, not a harness bug. Denied
calls are counted per run.

## Questions

Five questions, all in the two twinned areas, written the way a user would ask. Full text, reference
answers, checklists and automatic checks: [study-1/questions.toml](study-1/questions.toml).

| Id | Area | Prompt (short) | Why it's in the set |
|---|---|---|---|
| Q1 | modules | GROMACS with GPU support for a batch job | Expanse facts should help (`gpu` stack, hierarchy) |
| Q2 | modules | after `module purge`, `srun: command not found` | Expanse facts should help (`slurm` module, stack before `gcc`) |
| Q3 | conda | "Disk quota exceeded" in home after making envs | common; both skills should handle it |
| Q4 | conda | env on Lustre scratch, slow imports in multi-node jobs | Expanse facts should help (`$HOME`, conda-pack to node-local scratch) |
| Q5 | conda + modules | install TensorFlow with the R bindings | broad and hard; tests approach, not one fact |

Slurm-only questions are left out on purpose: `slurm` has no generic/Expanse pair, so they can't tell B from C.
The reference answers are `docs-only` until checked on Expanse
([verify-on-expanse](../expanse/verify-on-expanse.md), M1–M7 and C1–C5).

## Measures

Per run (from `opencode run --format json`; `skilleval.py score`):

- **Tokens:** sum over `step_finish` events of `input`, `output`, `reasoning`, and cache read/write (all
  zero on NRP so far).
- **Steps** (model calls), **tool calls**, **denied calls**, **wall time**.
- **Skill triggered:** whether the arm's expected skill was loaded (`skill` tool call).
- **Correctness:** pass/fail on the question's checklist, graded by a person from `answer.md` with the run's
  arm hidden. Automatic regex checks (`checks` in questions.toml) only screen answers and flag
  disagreements. They don't decide pass/fail.

Per arm and question: pass rate over repeats, median tokens, **tokens per solved task** (TPS = all tokens spent
on that question in that arm ÷ number of passing runs; infinite if none pass), trigger rate.

## Primary comparison (pre-registered)

**B vs C non-inferiority.** The generic skill is "good enough" if both hold, averaged over questions:

1. pass rate of B ≥ pass rate of C − **10 points**, and
2. TPS of B ≤ **1.2 ×** TPS of C (computed on the geometric mean of per-question ratios).

Secondary, exploratory: B vs A and C vs A on TPS and pass rate; per-question deltas (report how many
questions go the wrong way, not only the mean); trigger rate. With 5 questions the pilot reports these as
estimates with bootstrap intervals over questions, not as tests.

## Procedure

1. **Rehearse** in the minihpc `expanse-like` container (Lmod with Expanse-style stacks, Slurm client
   commands without a scheduler, Miniforge with an env on Lustre-style scratch), using the skilleval harness
   (published separately). This tests the harness and the skills' shell steps; its answers say nothing about
   Expanse and are not data.
2. **Expanse ground truth:** run the module and conda rows of the verify-on-Expanse checklist, and fix any
   reference answer they contradict **before** the pilot.
3. **Pilot** on an Expanse login node: `check-arms --probe`, then `run` (45 runs), then `score`.
4. **Grade** the 45 answers blind against the checklists; record the grades next to `runs.csv`.
5. **Report** the primary comparison, the per-question table, variance across repeats, and the
   number of questions and repeats the full study needs.

Changes after step 3 starts bump `version` in study.toml and are listed below.

## Threats to validity

- **Five questions.** Results can't generalise; the pilot only sizes the full study.
- **Model and host.** `nrp/gemma` stands in for the production Triton endpoint; same model family, but
  different serving. State it in any result.
- **Policy.** The allowlist isn't production's `ask`. A user who approves everything would let more through.
- **Graders.** One grader at first; a second grader on a subset gives agreement.
- **Nondeterminism.** Hosted inference at temperature 0.1 still varies; that is why there are 3 repeats.
- **Fixed tax.** B and C pay about 420–450 input tokens per request for the skill descriptions even when
  the skill isn't used. That is part of what's being measured, not noise.

## Rehearsal findings (2026-10-26, not data)

One repeat of every question × arm on a laptop and in the minihpc container (30 runs, all exit 0).

- Harness end to end works: packs, arm check, policy, token extraction, scoring.
- In the container, the Expanse modules skill ran its two shell calls (spider, dry-run) and produced the
  expected `gpu`-stack load line and batch block for Q1.
- **Q2 never triggered a modules skill** (0 of 4 runs across B and C, both environments). The agent answered
  from general knowledge ("remove `module purge`"). Neither skill description mentions `srun`/`sbatch`
  missing after a purge. Decide before the pilot: widen both descriptions the same way (and re-pin the SHAs)
  or keep Q2 as a trigger-failure case.
- The automatic checks are coarse (e.g. an arm-A answer to Q3 passed with no tool calls). Human grading stays
  the decision.

## Changes

| Date | Version | Change |
|---|---|---|
| 2026-10-26 | 1 | First version |
