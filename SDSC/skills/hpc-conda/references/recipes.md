# Conda recipes for HPC clusters

Read this when giving the user commands. Replace `<prefix>` (conda install dir), `<envdir>` (where the site
says envs go), `<env>`, `<account>`. If the user has `~/miniconda3` or a site conda module, swap it in for
`<prefix>`. Partition names and limits are site-specific: take them from the user or the `slurm` skill.

## Interactive job (use for every solve/install, if compute nodes have internet)

```bash
srun -A <account> -p <partition> -N 1 -n 1 -c 4 --mem=16G -t 01:00:00 --pty /bin/bash
```

## Install Miniforge

```bash
cd ~ && curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh -b -p <prefix> && rm Miniforge3-$(uname)-$(uname -m).sh
<prefix>/bin/conda config --set auto_activate_base false     # conda ≥ 25.5 may call this auto_activate
```

`-b` (batch mode) does not edit `~/.bashrc`. Only add `conda init bash` if the user wants `conda activate` at login.
To keep envs and the package cache out of home, add to `~/.condarc` (the user edits it):

```yaml
envs_dirs: [<envdir>]
pkgs_dirs: [<envdir>/pkgs]
```

## Create an env

```yaml
# environment.yml
name: <env>
channels: [conda-forge, nodefaults]
dependencies:
  - python=3.12
  - numpy=2.1
  - pip
```

```bash
source <prefix>/etc/profile.d/conda.sh
conda env create -f environment.yml          # or: -p <envdir>/<env>
conda clean -a -y
# GPU packages from a GPU-less node: CONDA_OVERRIDE_CUDA=12.4 conda env create -f environment.yml
```

## Use it in a job script

```bash
source <prefix>/etc/profile.d/conda.sh
conda activate <env>
export PYTHONNOUSERSITE=1
```

## conda-pack to node-local disk (multi-node or many-task jobs)

Pack it once, inside an interactive job:

```bash
source <prefix>/etc/profile.d/conda.sh
conda install -n base -y -c conda-forge conda-pack
conda pack -n <env> -o <envdir>/<env>.tar.gz
```

In the job script (use the site's node-local path; `$TMPDIR` if set, check `df -hT` that it is not tiny tmpfs):

```bash
ENV=${TMPDIR:-/tmp}/$USER/$SLURM_JOB_ID/<env>
mkdir -p "$ENV" && tar -xzf <envdir>/<env>.tar.gz -C "$ENV"
source "$ENV/bin/activate" && conda-unpack
# Multi-node: run the mkdir/tar on every node first: srun --ntasks-per-node=1 bash -c '...'
```

## Move an env

```bash
source <prefix>/etc/profile.d/conda.sh
conda env export -p <old-env-path> --from-history > <env>.yml   # top-level packages only
# Check <env>.yml (add versions, conda-forge channel), then (inside an interactive job):
conda env create -f <env>.yml -p <envdir>/<env>
conda env remove -p <old-env-path>
```

## Free home space

```bash
conda clean -a -y          # tarballs + unused package cache
pip cache purge
conda env list             # then: conda env remove -n <unused-env>
du -sh ~/* ~/.[!.]* 2>/dev/null | sort -h | tail -15
```

Big model and data caches (`~/.cache/huggingface`, `~/.cache/torch`) belong in project storage (few large files
are fine on a parallel filesystem), e.g. `export HF_HOME=<project-dir>/hf`.

## Switch to conda-forge

```bash
conda config --add channels conda-forge
conda config --set channel_priority strict
conda config --remove channels defaults
```

Existing envs keep the packages they were built with. Recreate them from `environment.yml` to switch fully.
Whether the institution may use `defaults` (Anaconda's terms) is a question for the user's IT/licensing office.

## mpi4py with the site MPI

Inside an interactive job on the target node type, with the MPI module from the `hpc-modules` skill:

```bash
module purge && module load <compiler>/<ver> <mpi>/<ver>
source <prefix>/etc/profile.d/conda.sh && conda activate <env>
MPICC=$(which mpicc) pip install --no-cache-dir --no-binary=mpi4py mpi4py
```

Alternative: conda-forge's external-MPI placeholder (`conda install -c conda-forge/label/mpi-external mpich`
or `openmpi`) so other conda packages use the system MPI. The job script must load the same modules before
`conda activate`.
