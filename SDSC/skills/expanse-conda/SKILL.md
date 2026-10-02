---
name: expanse-conda
description: >
  Use this skill whenever an Expanse user wants to install conda, mamba,
  Miniforge or Miniconda, create, use, move or fix a conda environment,
  activate one in a Slurm job or Jupyter/galyleo session, or hits conda
  problems on the cluster: "$HOME is full" / "Disk quota exceeded", slow
  Python imports, an environment on Lustre, conda breaking modules or Slurm,
  or mpi4py/CUDA mismatches inside a conda env.
license: MIT
compatibility: opencode
metadata:
  author: Yash Parikh
  updated: "2026-10-01"
  version: 0.1.0
  status: draft (docs-only; not yet tested on Expanse)
---

## Overview

- **Install conda and live environments in `$HOME`**, which is the Expanse user guide's advice. `$HOME` is NFS: 100 GB,
  backed up, never purged.
- **Never put a live environment on Lustre** (`/expanse/lustre/...`). An environment is tens of thousands of small
  files, so imports are slow and load the metadata server. Scratch is also purged and capped at 2 M files per user.
- Distribution: **Miniforge** (`~/miniforge3`, `conda-forge` only), as in SDSC's galyleo docs. An existing
  `~/miniconda3` is fine; don't make the user reinstall.
- Big, shared or many-node envs: `conda-pack` the env into one tarball and unpack it to node-local
  `/scratch/$USER/job_$SLURM_JOB_ID` in the job. PyTorch, TensorFlow, JAX and vLLM: suggest an SDSC/NGC container first.
- `base` auto-activating at login breaks modules and jobs. **Don't remove `conda init`**, because galyleo's
  `--conda-env` needs it. Set `auto_activate_base false` instead.
- Your shell is non-interactive, so `conda` isn't on `PATH`. Find it as in shell call 1.

## Procedure

1. **Audit (shell call 1).** Always run this first, read-only:

   ```bash
   for d in ~/miniforge3 ~/mambaforge ~/miniconda3 ~/anaconda3; do [ -x "$d/bin/conda" ] && C="$d/bin/conda" && break; done; echo "conda: ${C:-none}"; [ -n "$C" ] && { "$C" --version; "$C" env list; "$C" config --show channels auto_activate_base envs_dirs pkgs_dirs; du -sh "$("$C" info --base)/pkgs" 2>/dev/null; }; du -sh ~/.conda ~/.cache/pip ~/.local 2>/dev/null; grep -n 'conda initialize\|conda activate\|anaconda' ~/.bashrc ~/.bash_profile 2>/dev/null; timeout 60 du -sh ~ 2>/dev/null
   ```

2. **Report problems first, worst first.** Give a one-line fix for each and point to the recipe:
   1. Any env path under `/expanse/lustre` → recipe **Move an env off Lustre**.
   2. `$HOME` above ~80 GB, or a `pkgs` cache above a few GB → recipe **Free $HOME space**.
   3. `auto_activate_base: True` → `conda config --set auto_activate_base false`.
   4. `module load anaconda…` in `.bashrc` together with a personal conda → keep only one.
   5. Channels include `defaults` → recipe **Switch to conda-forge**.
   6. `conda: none` and the user wants conda → recipe **Install Miniforge**.

3. **Answer the request** with the matching recipe from
   [references/recipes.md](references/recipes.md). Fill in the user's env name, project and paths. Order:
   1. A one-line verdict (for example "your env is fine; the problem is X").
   2. Commands to run. Anything that solves or installs packages goes **inside an interactive job** (the recipe's
      `srun` line), never on the login node.
   3. Job-script activation lines, if they will use it in a job.

## Guidelines

- Prefer `mamba env create -f environment.yml` with pinned versions and `channels: [conda-forge, nodefaults]`
  over ad-hoc `conda install` chains.
- In job scripts: `source ~/miniforge3/etc/profile.d/conda.sh && conda activate <env>`, plus `export PYTHONNOUSERSITE=1`
  so packages in `~/.local` don't leak in.
- MPI codes: build `mpi4py` against the module MPI (recipe **mpi4py with module MPI**), not conda's MPI.
- GPU: take CUDA from the conda/pip packages, and don't also `module load cuda`. On V100 nodes (compute capability
  7.0), check that `torch.cuda.get_arch_list()` contains `sm_70`. NAIRR H100 nodes have no Lustre.
- Jupyter: galyleo `--conda-env <env>` (or `--conda-yml env.yml --mamba --cache`).

## Guardrails

- Read-only on the user's account: never run `conda create/install/remove`, `pip install` or `rm` yourself. Print
  them for the user.
- Never edit `~/.bashrc`, `~/.condarc` or other files. Show the line or command instead.
- Never suggest `/expanse/lustre` for a live env, or `conda init --reverse` for the `base` problem.

## References

- [references/recipes.md](references/recipes.md): read this when giving commands. Covers installing Miniforge,
  creating an env in an interactive job, job activation, conda-pack to node-local scratch, moving an env off
  Lustre, freeing `$HOME` space, switching to conda-forge, and mpi4py with module MPI.
- Expanse user guide: https://www.sdsc.edu/support/user_guides/expanse.html
- galyleo conda docs: https://github.com/mkandes/galyleo#conda
