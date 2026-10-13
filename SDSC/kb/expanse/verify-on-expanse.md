---
origin: kb
title: Verify-on-Expanse checklist (claims that need a live system)
author: Yash Parikh (illuminati1618)
updated: 2026-10-12
verified: docs-only
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). Everything in the KB marked `verified: docs-only` that an agent or skill would *act on*. Run these from an Expanse login node, paste the relevant output (redact other users' names and projects), then update the doc and its `verified:` field to `expanse-YYYY-MM-DD`.

# Verify-on-Expanse checklist

Why this exists: the public docs say partition limits are "subject to change", don't publish priority weights, and
are ambiguous about some charging boundaries. Some OpenCode behaviour is also undocumented: the
[config docs](https://opencode.ai/docs/config/) say `OPENCODE_CONFIG_DIR` is searched for agents, commands, modes and
plugins but don't mention skills, and the JSON event shapes aren't specified. A skill that states these as fact
needs real output behind it.

## Scheduler and partitions → [slurm-on-expanse](slurm-on-expanse.md)

| # | Command | Confirms | Status |
|---|---|---|---|
| S1 | `sinfo --version` | Slurm version: which man-page version applies, and whether `srun --overlap` (20.11+) and `scancel --me` exist. The [Expanse 101 tutorial](https://github.com/sdsc-hpc-training-org/expanse-101)'s old output shows `slurm/expanse/20.02.3` | ☐ |
| S2 | `sinfo -o "%P %a %l %D %c %m %G" \| column -t` | partitions, time limits, cores, memory, **GPU GRES strings** (`gpu:v100:4`? `gpu:h100:4`?) | ☐ |
| S3 | `scontrol show partition gpu-debug`, and the same for `gpu-shared`, `nairr-gpu-shared`, `debug`, `shared` | MaxTime, MaxNodes, DefMemPerCPU / DefMemPerGPU, QOS names | ☐ |
| S4 | `sacctmgr show qos format=Name%20,Priority,MaxWall,MaxTRESPU%40,MaxJobsPU,MaxSubmitPU,GrpTRES%30` | per-user vs per-group limits (table in slurm-on-expanse) | ☐ |
| S5 | `sprio -w` and `scontrol show config \| grep -i '^Priority'` | multifactor weights (fairshare, age, jobsize, partition, QOS) | ☐ |
| S6 | `sshare -U` | fair-share view is available to users | ☐ |
| S7 | Is there a debug queue for H100? `sinfo -p nairr-gpu-shared,nairr-gpu` and look for any `nairr-*debug*` | H100 debug option | ☐ |
| S8 | In any job: `echo $SLURM_TMPDIR; ls -d /scratch/$USER/job_$SLURM_JOB_ID` | Is `SLURM_TMPDIR` set at all ([known-issues A7](../hpcgpt-cli/known-issues.md))? | ☐ |
| S9 | `srun -p gpu-debug -A <p> --gpus=1 -t 5 --pty nvidia-smi` without `--mem` / `--cpus-per-task` | the default 1 CPU + 1 GB for a GPU job | ☐ |
| S10 | `srun -p nairr-gpu-shared -A <p> --gpus=h100:1 -t 5 --pty nvidia-smi --query-gpu=name,memory.total --format=csv` | H100 variant and memory (80 GB?) | ☐ |
| S11 | `ls /cm/shared/examples/sdsc/` | example-script tree to reference in skills | ☐ |
| S12 | `which mail` on login01/login02 | feedback plugin prerequisite ([known-issues B7](../hpcgpt-cli/known-issues.md)) | ☐ |
| S13 | `sinfo -o "%P %G" \| grep -i a100`; `scontrol show node exp-16-57` | which partition holds the A100 node seen in [mkandes/notes 2026/09/04](https://github.com/mkandes/notes/blob/main/2026/09/04.md), and whether regular allocations can use it ([gpu-selection](gpu-selection.md)) | ☐ |
| S14 | Ask consult@sdsc.edu, or note what happens when a project runs out: submit-time error, or a pending reason such as `AssocGrpBillingMinutes`? | how an exhausted allocation shows up | ☐ |
| S15 | `ls -ld /expanse/lustre/projects/<project>/$USER` | the project-space layout used in the KB's examples (the guide only names `/expanse/lustre/projects/`) | ☐ |

## Allocations → [allocations-and-sus](allocations-and-sus.md)

| # | Command | Confirms | Status |
|---|---|---|---|
| A1 | `expanse-client user -p -r expanse_nairr_gpu` | `user` output format for NAIRR. (The resource names and the `project` output for `expanse_nairr_gpu` are already in the [expanse-client skill](../../skills/expanse-client/SKILL.md).) | ☐ |
| A2 | Submit three 10-min `gpu-shared --gpus=1` jobs: (a) `-c 9 --mem=90G`, (b) `-c 10 --mem=92G`, (c) `-c 10 --mem=120G`, plus one `shared -c 1 --mem=2G` job. Compare `sacct -j <id> -o JobID,AllocTRES%60,Elapsed` (look at `billing=`) with the `expanse-client` usage delta, or ask consult@sdsc.edu | the exact GPU-SU boundary: the [guide's](https://www.sdsc.edu/systems/expanse/user_guide.html#job-charging) text (< 10 CPUs, < 92 GB) vs its example (10 cores, 96 GB). Possible explanation: ¼ of the allocatable `377308M` ≈ 92 GiB. Also whether `--mem=2G` per core bills at 1 SU (allocatable `249208M` ÷ 128 ≈ 1.9 GiB per core), and the H100 thresholds. **Skills currently state this as unverified.** | ☐ |
| A3 | Ask consult@sdsc.edu, or compare `expanse-client project` with the ACCESS portal for a project that got a supplement | whether `AVAILABLE` includes supplements and extensions (the skill's output has a project with 180 used of 150) | ☐ |

## Modules (Lmod) → `expanse-modules` skill (draft, branch `skill/expanse-modules`)

| # | Command | Confirms | Status |
|---|---|---|---|
| M1 | `module list; module -t avail cpu gpu 2>&1` on a login node | default login modules and current `cpu`/`gpu` stack versions (the [Expanse 101 tutorial](https://github.com/sdsc-hpc-training-org/expanse-101) shows `cpu/0.15.4`; the [galyleo README](https://github.com/sdsc/galyleo)'s example uses `cpu/0.17.3b`) | ☐ |
| M2 | `module -t spider gromacs 2>&1` | terse spider prints one `name/version` per line (the skill's step 1 depends on it) | ☐ |
| M3 | `module spider gromacs/<ver> 2>&1` | the "need to load ... any one of the lines below" layout the skill's awk parses; a Core package prints "can be loaded directly" | ☐ |
| M4 | In the agent's non-interactive shell: `source /etc/profile.d/modules.sh; module purge; module load gpu slurm 2>&1; module list 2>&1` **on a login node** | the `gpu` stack can be dry-run-loaded on login nodes (not only on GPU nodes) | ☐ |
| M5 | `module purge; module load cpu; module load <pkg>` with no version, then `module list` | Lmod resolves the stack's default version without `(D)` being shown by spider | ☐ |
| M6 | On a `nairr-gpu-shared` node: `module list; module spider cuda 2>&1` | which software stack the H100 nodes use | ☐ |
| M7 | `module -t spider py-numpy anaconda3 singularitypro cuda 2>&1` | the module names the skill suggests exist | ☐ |

## Conda → `expanse-conda` skill (draft, branch `skill/expanse-conda`)

| # | Command | Confirms | Status |
|---|---|---|---|
| C1 | On a `nairr-gpu-shared` node: `ls ~ && df -h ~` | `$HOME` is mounted on NAIRR H100 nodes. The [guide](https://www.sdsc.edu/systems/expanse/user_guide.html#expanse-ai-resource) says the AI resource shares the home directories; confirm, since the skill assumes envs in `$HOME` work there | ☐ |
| C2 | In a `shared` job: `curl -sI https://conda.anaconda.org/conda-forge/ \| head -1` | compute nodes can reach conda-forge. Evidence so far: in [mkandes/notes 2026/06/13b](https://github.com/mkandes/notes/blob/main/2026/06/13b.md) a galyleo `--conda-yml` build from conda-forge and `npm i -g opencode-ai` both succeeded on a compute node (`debug` partition) | ☐ |
| C3 | Is there a fast per-user quota command (`quota -s`, `lfs quota`, SDSC tool)? | replace the skill's slow `timeout 60 du -sh ~` | ☐ |
| C4 | Full conda-pack recipe in a job: unpack to `/scratch/$USER/job_$SLURM_JOB_ID`, `conda-unpack`, `python -c "import numpy"` | the recipe works end to end | ☐ |
| C5 | `module spider anaconda3 2>&1` | whether a site `anaconda3`/`miniconda` module exists | ☐ |

## OpenCode / hpcgpt-cli → [architecture](../hpcgpt-cli/architecture.md), [extending-skills](../hpcgpt-cli/extending-skills.md)

| # | Command | Confirms | Status |
|---|---|---|---|
| O1 | `opencode --version` (after `npm i -g opencode-ai`) | V1 version actually installed on Expanse (local sandbox: 1.18.32 ✓) | ☐ |
| O2 | `OPENCODE_CONFIG_DIR=<pack copy> opencode debug skill` | **Confirmed 2026-09-27 (local sandbox, 1.18.32):** `OPENCODE_CONFIG_DIR` loads config, agents and skills (`expanse-client`, `slurm`, plus draft skills). Also revealed [known-issues A0](../hpcgpt-cli/known-issues.md). | ☑ |
| O3 | (apply the A0 fix first, or `--agent hpcgpt` is the allow-everything agent) `opencode run --agent hpcgpt --format json "check my GPU allocation" \| head -50` | JSON event shape of a `skill` tool call, to fix the grep in the trigger tests | ☐ |
| O4 | Start the opencode TUI with the `chat` MCP server **not** running | how an MCP connection failure shows up in the TUI (`opencode mcp list` already shows "✗ chat failed", checked locally with 1.18.32) | ☐ |
| O8 | `OPENCODE_CONFIG_CONTENT` overlay from [dev-workflow](../hpcgpt-cli/dev-workflow.md) step 0, then `opencode debug config \| grep -n '"model"'` | the overlay works on Expanse as it does locally | ☐ |
| O9 | `echo ${TRITON_AI_API_KEY:+set}` after following SDSC's setup | the Triton key variable name is `TRITON_AI_API_KEY` (one older setup note says `TRITONAI_API_KEY`) | ☐ |
| O10 | `OPENCODE_TUI_CONFIG=<pack>/tui.jsonc opencode` from a different working directory, then `/jobs` | TUI plugin paths in `tui.jsonc` resolve relative to that file, not the cwd | ☐ |
| O5 | `OPENCODE_TUI_CONFIG=.../SDSC/tui.jsonc opencode`, then `/jobs` | V1 TUI plugins load on Expanse (bun and solid-js resolution) | ☐ |
| O6 | `curl -s -H "Authorization: Bearer $NRP_LLM_API_KEY" https://ellm.nrp-nautilus.io/v1/models` **from a login node** | outbound HTTPS to NRP allowed from Expanse | ☐ |
| O7 | `opencode run --agent hpcgpt -m nrp/qwen3 --format json "hi"` and check the model in the events | whether `-m` overrides the agent's pinned `model:` | ☐ |

## Recording results

Put outputs in `SDSC/kb/expanse/transcripts/<date>-<topic>.md` (KB doc frontmatter, `verified: expanse-<date>`),
link them from the row, and tick the box. Transcripts are the most valuable input for skills: the existing SDSC skills are built
around real `[user@login01 ~]$` sessions.
