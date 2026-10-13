---
origin: kb
title: Expanse allocations, Service Units (SUs) and expanse-client
author: Yash Parikh (illuminati1618)
updated: 2026-10-12
verified: docs-only
sources:
  - expanse-user-guide
  - expanse-access-page
  - expanse-nairr-allocations
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). The charging rules come from the [user guide, Job Charging](https://www.sdsc.edu/systems/expanse/user_guide.html#job-charging) (checked against the live page, October 2026). `expanse-client` usage follows the [expanse-client skill](../../skills/expanse-client/SKILL.md), which contains real output.

# Expanse allocations, SUs and `expanse-client`

## Where allocations come from

| Resource (`expanse-client resource`) | Hardware | Obtained via |
|---|---|---|
| `expanse` | CPU nodes (compute/shared/debug/large-shared/preempt) | ACCESS allocation ([allocations.access-ci.org](https://allocations.access-ci.org/)) |
| `expanse_gpu` | V100 nodes | ACCESS allocation (GPU resources are allocated separately from CPU) |
| `expanse_nairr_gpu` | H100 nodes (Expanse AI resource) | [NAIRR Pilot](https://nairrpilot.org/opportunities/allocations) |
| `expanse_industry`, `expanse_industry_gpu` | `ind-*` partitions | industry agreements |

The resource names are from real `expanse-client resource` output in the skill. The guide's own example output
is older and omits `expanse_nairr_gpu`.

A **project** (such as `abc123`) is a Linux group and the value for `--account`. Its ACCESS grant number (`TG-XXX123456`)
is shown alongside it but **isn't** what you pass to Slurm. The [guide](https://www.sdsc.edu/systems/expanse/user_guide.html#technical-summary) caps a PI at 15 M core-hours and 75 K GPU-hours.
PIs and co-PIs add or remove users on the **Manage Allocations** page of the
[ACCESS allocations portal](https://allocations.access-ci.org/), which is also where ACCESS renewals and
extensions are requested. Account problems (for example an allocation in the `amied` state) go to
consult@sdsc.edu, per the hpcGPT agent's escalation rules (`SDSC/agents/hpcgpt.md`).

## Charging

- **1 SU** = 1 core-hour using ≤ 2 GB, **or** 1 GPU-hour using < 92 GB, in the guide's words. Its charging bullets
  add that a GPU SU is "1GPU, <10CPUs, and <92G of memory".
- **Shared-type partitions** (`shared`, `gpu-shared`, `debug`, `gpu-debug`, `large-shared`): charged on "either the
  number of cores or the fraction of the memory requested, whichever is larger" × hours. You pay for what you
  *reserve*, not what you use. On CPU partitions this works out to about memory ÷ 2 GB, which matches both the
  1-SU definition and the guide's large-shared example (2 TB for 1 h = 1024 SU).
- **Exclusive partitions** (`compute`, `gpu`): the whole node. That's 128 SU/h on compute, and 4 GPU-SU/h on a gpu
  node. `nairr-gpu` is also exclusive, but the guide doesn't give its charging rule.
- `preempt`, `gpu-preempt`: charge factor 0.8, **non-refundable** if preempted.
- Minimum charge is 1 SU per job.

**The exact boundaries are ambiguous** ([verify A2](verify-on-expanse.md)):

- GPU: the guide's `gpu-debug` example asks for 10 cores + 96 GB with one GPU, which is ¼ of the nominal 40 cores /
  384 GB, while the text says < 10 CPUs and < 92 GB. One possible explanation (not confirmed): the documented
  maximum `--mem=377308M` ÷ 4 ≈ 92 GiB, so 92 GB may be ¼ of the *allocatable* memory.
- CPU: the maximum `--mem=249208M` ÷ 128 cores ≈ 1.9 GiB per core, so `--mem=2G` per core may bill slightly
  above 1 SU per core-hour.
- The memory and CPU thresholds for an H100 GPU-SU aren't documented at all.

Worked examples (≈, assuming a 2 GB-per-core divisor on CPU nodes):

| Request | Charge |
|---|---|
| `-p shared --cpus-per-task=1 --mem=2G -t 1:00:00` | ≈ 1 SU |
| `-p shared --cpus-per-task=4 --mem=32G -t 2:00:00` | memory dominates: 32 GB ÷ 2 GB = 16 core-equivalents × 2 h ≈ **32 SU** (≈ 8 SU with `--mem=8G`) |
| `-p compute -N 2 -t 3:00:00` | 2 × 128 × 3 = **768 SU** |
| `-p gpu-shared --gpus=1 --cpus-per-task=10 --mem=92G -t 5:00:00` | **≈ 5 GPU-SU** (exact boundary unverified, see above) |
| `-p gpu -N 1 -t 5:00:00` (used 1 GPU) | **20 GPU-SU** (whole node) |

## `expanse-client` (on Expanse; `module load sdsc` if missing)

```bash
expanse-client resource                               # list allocatable resources
expanse-client user -p                                # my projects on `expanse` (CPU; the default resource)
expanse-client user -p -r expanse_gpu                 # my projects on V100 GPU
expanse-client project <project> -p -r expanse_gpu    # per-user usage within a project + expiration
```

`user -p` columns: `NAME`, `STATE` (`allow` = can charge the project; the skill names `amied` as the other state),
`PROJECT` (use this for `--account`), `TG PROJECT` (grant id), `USED` (by this user), `AVAILABLE` (total awarded to
the project), `USED BY PROJECT`. The `project -p` output calls the state column `STATUS`.

**Remaining ≈ AVAILABLE − USED BY PROJECT.** For example, `use300` shows 79000 available and 72252 used, so about
6.7 K GPU-SU are left. The result can be negative: one row in the skill shows 180 used of 150. Whether
`AVAILABLE` includes supplements and extensions is unverified ([verify A3](verify-on-expanse.md)).

An agent answering "how many hours do I have left?" should run the `user` command for **both** `expanse` and
`expanse_gpu` (and `expanse_nairr_gpu` if relevant), then compute the remaining balance per project.
