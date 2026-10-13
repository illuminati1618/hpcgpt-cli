---
origin: kb
title: Slurm on Expanse — partitions, interactive + batch syntax, monitoring, priority
author: Yash Parikh (illuminati1618)
updated: 2026-10-12
verified: docs-only
sources:
  - expanse-user-guide
  - expanse-101
  - expanse-interactive-computing
  - expanse-batch-computing-batch
  - slurm-sbatch
  - slurm-srun
  - slurm-squeue
  - slurm-priority-multifactor
  - slurm-sprio
  - slurm-salloc
  - slurm-sacct
  - slurm-sinfo
  - slurm-scontrol
  - slurm-job-arrays
  - expanse-batch-computing-fairshare
  - expanse-hpctr-examples
  - slurm-man-index
  - slurm-job-reason-codes
  - slurm-scancel
  - slurm-sshare
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). Expanse-specific Slurm usage for agents and skills. Upstream authority: [Expanse User Guide, Running Jobs](https://www.sdsc.edu/systems/expanse/user_guide.html#running-jobs-on-expanse) (checked against the live page, October 2026). Generic Slurm flags: the [Slurm man pages](https://slurm.schedmd.com/man_index.html). The guide says partition limits are "subject to change", so re-check them with `scontrol show partition` ([verify-on-expanse](verify-on-expanse.md)).

# Slurm on Expanse

## The four things every Expanse job needs

1. **`--account=<project>`**: required. The project is the Linux group name (for example `abc123`, not the `TG-...`
   grant number). List yours with `expanse-client user -p` (CPU) and `expanse-client user -p -r expanse_gpu`
   (GPU). CPU and GPU are **separate allocations**, so a project may have one and not the other. See [allocations-and-sus](allocations-and-sus.md).
2. **`--partition=`**: picks node type, sharing, and charging. See the table below.
3. **`--time=`** (`-t`): hard wall-clock limit. Shorter jobs backfill sooner.
4. **Resources that match the partition**:
   - *shared-type partitions* (`shared`, `gpu-shared`, `debug`, `gpu-debug`, `large-shared`, `nairr-gpu-shared`):
     request cores (`--ntasks`/`--cpus-per-task`), `--mem`, and `--gpus`. **The default is 1 GB per core, and
     1 GPU gets 1 CPU + 1 GB** ([guide, Job Charging](https://www.sdsc.edu/systems/expanse/user_guide.html#job-charging)), which is almost never what a GPU job wants.
   - *exclusive partitions* (`compute`, `gpu`, `nairr-gpu`): you get and **pay for** whole nodes. Use
     `--mem=0` to get all the memory (the [guide's MPI example](https://www.sdsc.edu/systems/expanse/user_guide.html#running-jobs-on-expanse)) or the documented maximum (`--mem=377308M` on gpu).

Plus, when relevant: `--gpus=<n>` (V100 partitions) or **`--gpus=h100:<n>`** (NAIRR partitions, where the type is
mandatory), and `--constraint="lustre"` if the job touches `/expanse/lustre/...` (otherwise it fails).

## Partitions (from the user guide, 2026-10-12)

| Partition | Node type | Sharing | Max wall | Max nodes/job | Max running / running+queued jobs | Charge ×  | Use it for |
|---|---|---|---|---|---|---|---|
| `debug` | CPU (shared nodes) | shared | **30 min** | 2 | 1 / 2 | 1 | testing a CPU script; priority access |
| `shared` | CPU | shared | 48 h | 1 | 4096 / 4096 | 1 | < 128 cores on one node |
| `compute` | CPU | exclusive | 48 h | 32 | 32 / 64 (**per group**) | 1 | MPI, full nodes |
| `large-shared` | 2 TB RAM | shared | 48 h | 1 | 1 / 4 | 1 | needs > 256 GB RAM (min 256 G) |
| `gpu-debug` | 4× V100 | shared | **30 min** | 2 | 1 / 2 | 1 | testing a GPU script; **max 2 GPUs/job** |
| `gpu-shared` | 4× V100 | shared | 48 h | 1 | 24 / 24 (24 GPU TRES) | 1 | 1–3 GPUs on one node |
| `gpu` | 4× V100 | exclusive | 48 h | 4 | 4 / 8 (32 GPU TRES) | 1 | 4 GPUs/node, multi-node |
| `nairr-gpu-shared` | 4× H100 | shared | 48 h | 1 | 16 / 16 | 1 | 1–3 H100s (NAIRR allocation only) |
| `nairr-gpu` | 4× H100 | exclusive | 48 h | 4 | 4 / 8 (32 GPU TRES) | 1 | full H100 nodes |
| `preempt` | CPU | – | 7 days | 32 | – / 128 | **0.8** | restartable work; **killed** by any other queue; non-refundable |
| `gpu-preempt` | V100 | – | 7 days | 1 | – / 24 | **0.8** | restartable GPU work |
| `ind-*` | industry nodes | | | | | | industry allocations only |

The [guide](https://www.sdsc.edu/systems/expanse/user_guide.html#running-jobs-on-expanse) says job limits apply "on a per group (allocation) and partition basis", and repeats "per group" for
`compute`. Confirm the actual QOS limits with `sacctmgr show qos` ([verify S4](verify-on-expanse.md)). Exact source
table: [user guide, Running Jobs](https://www.sdsc.edu/systems/expanse/user_guide.html#running-jobs-on-expanse).
Only use `preempt` partitions if the job checkpoints and can restart (the SDSC `slurm` skill has the same rule).

## Interactive jobs

From the guide, with `<project>` filled in. **These are the commands users most often get wrong:**

```bash
# CPU debug: 4 cores, 8 GB, 30 min
srun --partition=debug --pty --account=<project> --nodes=1 --ntasks-per-node=4 \
     --mem=8G -t 00:30:00 --wait=0 --export=ALL /bin/bash

# GPU debug: 1 V100, 10 cores, 96 GB, 30 min  (then: module purge; module restore)
srun --partition=gpu-debug --pty --account=<project> --nodes=1 --ntasks-per-node=10 \
     --mem=96G --gpus=1 -t 00:30:00 --wait=0 --export=ALL /bin/bash

# Longer GPU interactive (up to 48 h, but you're charged while idle): gpu-shared, 1 V100
srun --partition=gpu-shared --pty --account=<project> --nodes=1 --ntasks-per-node=10 \
     --mem=92G --gpus=1 -t 02:00:00 --wait=0 --export=ALL /bin/bash

# H100 (NAIRR allocation): the GPU type is mandatory
srun --partition=nairr-gpu-shared --pty --account=<project> --nodes=1 --ntasks-per-node=18 \
     --mem=250G --gpus=h100:1 -t 01:00:00 --wait=0 --export=ALL /bin/bash
```

- About 10 cores and ~92 GB per V100 is a quarter node. Whether that bills as exactly one GPU-SU is **unverified**:
  the guide's charging text says a GPU SU is 1 GPU with **< 10 CPUs and < 92 GB**, but its own `gpu-debug` example
  requests 10 cores and **96 GB**. Treat 10 cores / 92 GB as "≈ 1 GPU-SU" until [verify A2](verify-on-expanse.md)
  settles it (details in [allocations-and-sus](allocations-and-sus.md#charging)).
- The H100 line's 18 cores / 250 GB per GPU is a proportional ¼ node (72 cores, 1 TB). The GPU-SU memory and CPU
  thresholds for NAIRR nodes are **not documented**, so check with SDSC ([verify-on-expanse](verify-on-expanse.md)).
- `salloc` works too: `salloc -p gpu-debug -A <project> -N 1 --gpus=1 --ntasks-per-node=10 --mem=96G -t 30`, then
  `srun --pty bash` to get a shell on the allocated node (the guide itself only shows `srun --pty`).
- Once on the node: `module purge; module restore` (the guide's instruction), then `module load gpu`, `nvidia-smi`,
  `echo $CUDA_VISIBLE_DEVICES`.
- Exit the shell (or `scancel <jobid>`) as soon as you're done. Idle interactive time is still charged.

## Batch templates

Canonical examples: `/cm/shared/examples/sdsc/` on Expanse, and [hpctr-examples](https://github.com/sdsc-hpc-training-org/hpctr-examples).

```bash
#!/usr/bin/env bash
#SBATCH --job-name=train-1gpu
#SBATCH --account=<project>
#SBATCH --partition=gpu-shared
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=10
#SBATCH --gpus=1
#SBATCH --mem=92G
#SBATCH --time=04:00:00
#SBATCH --constraint="lustre"          # only if reading/writing /expanse/lustre
#SBATCH --output=%x.o%j.%N
#SBATCH --no-requeue                   # optional: Slurm requeues on node failure (up to 5 times) unless you set this

module purge
module load gpu
module load slurm
# module load singularitypro  |  source ~/miniforge3/etc/profile.d/conda.sh && conda activate myenv

cd /scratch/$USER/job_$SLURM_JOB_ID    # node-local NVMe; copy inputs in, results out
cp -r /expanse/lustre/projects/<project>/$USER/data ./
python train.py --data ./data --out ./ckpt
cp -r ./ckpt /expanse/lustre/projects/<project>/$USER/results/$SLURM_JOB_ID
```

CPU variants:
- **Shared, 8 cores and 16 GB:** `-p shared --ntasks=1 --cpus-per-task=8 --mem=16G`. You're charged the larger of
  8 cores and 16 GB ÷ 2 GB, so ≈ 8 SU/h.
- **Exclusive MPI:** `-p compute --nodes=2 --ntasks-per-node=128 --mem=0`, then `module load slurm` and
  `srun --mpi=pmi2 -n 256 ./app`, as in the guide's MPI example. You're charged 256 SU/h whatever you use.

Dependencies and arrays:

```bash
jid=$(sbatch --parsable prep.sb); sbatch --dependency=afterok:$jid train.sb
sbatch --array=0-99%10 sweep.sb        # 100 tasks, at most 10 running; use $SLURM_ARRAY_TASK_ID
```

The guide asks users to **contact SDSC consulting before submitting a lot of jobs** (especially very short ones),
because they slow the scheduler for everyone. Bundle them (arrays, GNU parallel inside one job, or multiple `srun`
steps in one allocation).

## Monitoring and debugging

```bash
squeue --me                                  # R = running, PD = pending (+ reason)
squeue --me --start                          # scheduler's estimated start time
scontrol show job <jobid>                    # full request as Slurm understood it
sacct -j <jobid> --format=JobID,JobName,Partition,State,ExitCode,Elapsed,MaxRSS,ReqMem,AllocTRES%40,NodeList
sstat -j <jobid>.batch --format=MaxRSS,AveCPU  # live usage of a running step
scancel <jobid>   |   scancel -u $USER -t PENDING
sinfo -p gpu-debug,gpu-shared -o "%P %a %l %D %t %G"   # partition state, limits, GPUs
```

Pending reasons (the `NODELIST(REASON)` column) and what to tell the user:

| Reason | Meaning ([Slurm reason codes](https://slurm.schedmd.com/job_reason_codes.html)) | Action |
|---|---|---|
| `Priority` | Higher-priority jobs are ahead | Wait; shorter `--time` helps backfill; see `sprio -j <id>` |
| `Resources` | Next in line; waiting for nodes to free up | Wait |
| `AssocMaxJobsLimit`, `QOSMaxJobsPerUserLimit`, `QOSMaxGRESPerUser`, `QOSMaxCpuPerUserLimit`… | You (or your group: Expanse limits are per allocation) hit a job or resource limit from the table above | Wait for running jobs to finish, or consolidate |
| `AssocGrpBillingMinutes` / other `AssocGrp*` | A group-level cap; possibly the allocation is used up. How Expanse shows an exhausted allocation is unverified ([verify S14](verify-on-expanse.md)) | `expanse-client project <p> -p -r <resource>`; the PI renews or extends via ACCESS |
| `ReqNodeNotAvail` (often followed by `Reserved for maintenance`) | Nodes the job needs are reserved, down or drained | `scontrol show reservation`; shorten `--time` to finish before the reservation, or wait |
| `Dependency` / `DependencyNeverSatisfied` | Waiting on `--dependency` / the parent failed | `scancel` and fix the chain |

Frequent failures:

| Symptom | Likely cause | Fix |
|---|---|---|
| `Invalid account or account/partition combination specified` | Wrong project, or a CPU-only project on a GPU partition | `expanse-client user -p -r expanse_gpu` |
| Job ends `OUT_OF_MEMORY` / `oom-kill` | Default 1 GB/core on shared partitions | Set `--mem` explicitly; check `MaxRSS` in `sacct` |
| Job fails immediately reading `/expanse/lustre/...` | Missing `--constraint="lustre"` (or the job is on an H100 node, where Lustre isn't mounted) | Add the constraint; on `nairr-gpu*` use local NVMe + Ceph S3 |
| `CUDA error: no kernel image` / bf16 errors on V100 | V100 is compute capability 7.0: no bf16, no FlashAttention-2 | See [gpu-selection](gpu-selection.md) |
| `module: command not found` in the job | Non-login shell | `source /etc/profile.d/modules.sh` |

## Priority (how the queue orders jobs)

SDSC doesn't publish how Expanse orders the queue. It is probably Slurm's
[multifactor priority](https://slurm.schedmd.com/priority_multifactor.html) plugin, but that is unconfirmed until
[verify S5](verify-on-expanse.md). The fair-share chapter of SDSC's batch-computing tutorial
([FAIRSHARE.md](https://github.com/mkandes/batch-computing/blob/main/FAIRSHARE.md)) is still empty. What an agent can do:

```bash
sprio -w                     # the configured weights (age, fairshare, jobsize, partition, QOS)
sprio -j <jobid>             # this job's factor breakdown
sshare -U -A <project>       # fair-share: your usage vs. shares
scontrol show config | grep -i '^Priority'
```

Under multifactor priority, jobs that wait longer gain age priority and projects that have used more than their
share lose fair-share priority. The guide calls `debug`/`gpu-debug` "priority access" partitions for short tests. Record real `sprio -w` output in
[verify-on-expanse](verify-on-expanse.md) before a skill states weights as fact.
