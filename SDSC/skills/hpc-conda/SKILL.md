---
name: hpc-conda
description: >
  Use this skill whenever an HPC cluster user wants to install conda, mamba,
  Miniforge or Miniconda, create, use, move or fix a conda environment,
  activate one in a Slurm job or Jupyter session, or hits conda problems on
  the cluster: "Disk quota exceeded" in home, too many files, slow Python
  imports, an environment on a parallel filesystem (Lustre, GPFS), conda
  breaking modules or Slurm, a CPU-only PyTorch build, or mpi4py/CUDA
  mismatches inside a conda env.
license: MIT
compatibility: opencode
metadata:
  author: Yash Parikh
  updated: "2026-10-12"
  version: 0.1.0
  status: draft (docs-only; generic twin of expanse-conda)
---

## Overview

Sites disagree on **where** envs belong (home, project, a software filesystem, scratch copied at run time),
so discover the filesystems in step 1 and **ask** rather than assume. What every site agrees on:

- **Home is small** (space and file-count quotas). A conda install plus its `pkgs` cache can use half a home
  file quota. Keep caches small; put big envs where the site says.
- **Don't run big envs straight off a parallel filesystem** (Lustre, GPFS) at scale: tens of thousands of
  small files → slow imports and metadata load. **Never** put a long-lived env on **purged** scratch.
- Distribution: **Miniforge** (`conda-forge` only; Mambaforge is retired). An existing Miniconda/Anaconda is
  fine; don't make the user reinstall. The Anaconda `defaults` channel needs a paid or academic license at many
  institutions: flag it as a **policy question**, not an error.
- Some sites discourage conda (prefer venv on a module Python, or containers). If the site docs say so, follow them.
- `base` auto-activating at login breaks modules and jobs: turn auto-activation off, don't uninstall conda.
- Your shell is non-interactive, so `conda` may not be on `PATH`. Find it as in shell call 1.

## Procedure

1. **Audit (shell call 1).** Always run this first, read-only:

   ```bash
   C="${CONDA_EXE:-$(command -v conda)}"; for d in ~/miniforge3 ~/mambaforge ~/miniconda3 ~/anaconda3; do [ -z "$C" ] && [ -x "$d/bin/conda" ] && C="$d/bin/conda"; done; echo "conda: ${C:-none}"; [ -z "$C" ] && (type module >/dev/null 2>&1 && module -t avail 2>&1 | grep -iE 'conda|forge|mamba|python'); [ -n "$C" ] && { "$C" --version; "$C" env list; "$C" config --show channels channel_priority envs_dirs pkgs_dirs solver 2>&1; "$C" config --show auto_activate_base 2>&1; "$C" config --show auto_activate 2>&1; R=$("$C" info --base); du -sh "$R/pkgs" 2>/dev/null; df -hT "$R" 2>/dev/null | tail -1; }; env | grep -E '^(HOME|SCRATCH|WORK|PROJECT|TMPDIR)='; df -hT ~ ${SCRATCH:-} ${WORK:-} ${PROJECT:-} 2>/dev/null; quota -s 2>/dev/null | tail -3; du -sh ~/.conda ~/.cache/pip ~/.local 2>/dev/null; grep -n 'conda initialize\|conda activate\|module load.*conda' ~/.bashrc ~/.bash_profile 2>/dev/null
   ```

   Run `"$C" env list` paths through `df -hT` / `stat -f -c %T` if any look like a shared filesystem.

2. **Report problems first, worst first.** Give a one-line fix for each and point to the recipe:
   1. Any env on a `lustre`/`gpfs` filesystem used by multi-node jobs, or on purged scratch → recipe **Move an env**.
   2. Home near its quota, or a `pkgs` cache above a few GB → recipe **Free home space**.
   3. `auto_activate_base: True` (or `auto_activate: True`) → turn it off (recipe **Install Miniforge**, last line).
   4. A conda module loaded in `.bashrc` together with a personal conda → keep only one.
   5. Channels include `defaults`, or `channel_priority` isn't `strict` → recipe **Switch to conda-forge**
      (and mention the license question).
   6. `conda: none` and the user wants conda → recipe **Install Miniforge** (or the site's conda module if one exists).

   If the right location for envs is unclear, **ask one question:** "Does your center's documentation say where
   conda environments should go (home, project space, or a software filesystem), and is scratch purged?"

3. **Answer the request** with the matching recipe from
   [references/recipes.md](references/recipes.md). Fill in the user's env name, paths and account. Order:
   1. A one-line verdict (for example "your env is fine; the problem is X").
   2. Commands to run. Anything that solves or installs packages goes **inside an interactive job** if compute
      nodes have internet, otherwise on the login node with a small pinned `environment.yml`.
   3. Job-script activation lines, if they will use it in a job.

## Guidelines

- Prefer `conda env create -f environment.yml` (libmamba is the default solver since conda 23.10; `mamba` also
  works) with pinned versions and `channels: [conda-forge, nodefaults]` over ad-hoc `conda install` chains.
- In job scripts: `source <prefix>/etc/profile.d/conda.sh && conda activate <env>`, plus `export PYTHONNOUSERSITE=1`
  so packages in `~/.local` don't leak in.
- MPI codes: use the site's MPI (recipe **mpi4py with the site MPI**), not conda's own MPI.
- GPU: take CUDA from the conda/pip packages and don't also load a CUDA module. Creating an env on a GPU-less
  login node picks CPU builds: create it in a GPU job, or set `CONDA_OVERRIDE_CUDA=<ver>`.
- conda-pack to node-local disk only pays off for multi-node or many-task jobs; don't push it for small jobs.
- Pure-PyPI projects: a venv (or uv) on the site's Python module is a valid, lighter alternative; mention it in one line.

## Guardrails

- Read-only on the user's account: never run `conda create/install/remove`, `pip install` or `rm` yourself. Print
  them for the user.
- Never edit `~/.bashrc`, `~/.condarc` or other files. Show the line or command instead.
- Never recommend purged scratch for a long-lived env, or `conda init --reverse` for the `base` problem.
- Never state a site's quota, purge policy or recommended path unless the audit output or the user showed it.

## References

- [references/recipes.md](references/recipes.md): read this when giving commands. Covers installing Miniforge,
  creating an env, job activation, conda-pack to node-local disk, moving an env, freeing home space, switching to
  conda-forge, and mpi4py with the site MPI.
- conda-forge tips (channels, CUDA override, external MPI): https://conda-forge.org/docs/user/tipsandtricks/
- conda-pack: https://conda.github.io/conda-pack/
