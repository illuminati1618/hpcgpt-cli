# Conda recipes for Expanse

Read this when giving the user commands. Replace `<project>`, `<env>` and `<group>`. If the user has
`~/miniconda3`, swap it in for `~/miniforge3`.

## Interactive job (use for every solve/install)

```bash
srun -p shared -A <project> -N 1 -n 1 -c 4 --mem=16G -t 01:00:00 --pty --wait=0 --export=ALL /bin/bash
```

## Install Miniforge

```bash
cd ~ && curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
bash Miniforge3-Linux-x86_64.sh -b -p ~/miniforge3 && rm Miniforge3-Linux-x86_64.sh
~/miniforge3/bin/conda init bash                    # needed for galyleo --conda-env
~/miniforge3/bin/conda config --set auto_activate_base false
```

## Create an env (inside the interactive job)

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
source ~/miniforge3/etc/profile.d/conda.sh
mamba env create -f environment.yml
conda clean -a -y
```

## Use it in a job script

```bash
source ~/miniforge3/etc/profile.d/conda.sh
conda activate <env>
export PYTHONNOUSERSITE=1
```

## conda-pack to node-local scratch (big, shared or many-node envs)

Pack it once, inside an interactive job:

```bash
source ~/miniforge3/etc/profile.d/conda.sh
mamba install -n base -y conda-pack
mkdir -p /expanse/lustre/projects/<group>/$USER/envs
conda pack -n <env> -o /expanse/lustre/projects/<group>/$USER/envs/<env>.tar.gz
```

In the job script (add `#SBATCH --constraint="lustre"`):

```bash
ENV=/scratch/$USER/job_$SLURM_JOB_ID/<env>
mkdir -p "$ENV" && tar -xzf /expanse/lustre/projects/<group>/$USER/envs/<env>.tar.gz -C "$ENV"
source "$ENV/bin/activate" && conda-unpack
# Multi-node: run the mkdir/tar on every node first, with: srun --ntasks-per-node=1 bash -c '...'
```

## Move an env off Lustre

```bash
source ~/miniforge3/etc/profile.d/conda.sh
conda env export -p <lustre-env-path> --from-history > <env>.yml   # top-level packages only
# Check <env>.yml (add versions, conda-forge channel), then inside an interactive job:
mamba env create -f <env>.yml
conda env remove -p <lustre-env-path>
```

## Free $HOME space

```bash
conda clean -a -y          # tarballs + unused package cache
pip cache purge
conda env list             # then: conda env remove -n <unused-env>
du -sh ~/* ~/.[!.]* 2>/dev/null | sort -h | tail -15
```

Big model and data caches (`~/.cache/huggingface`, `~/.cache/torch`) belong in project storage: few large files are
fine on Lustre. Use `export HF_HOME=/expanse/lustre/projects/<group>/$USER/hf`.

## Switch to conda-forge

```bash
conda config --add channels conda-forge
conda config --set channel_priority strict
conda config --remove channels defaults
```

Existing envs keep the packages they were built with. Recreate them from `environment.yml` to switch fully.

## mpi4py with module MPI

Inside an interactive job on the target node type:

```bash
module purge && module load cpu slurm gcc openmpi         # pin versions per the expanse-modules skill
source ~/miniforge3/etc/profile.d/conda.sh && conda activate <env>
MPICC=$(which mpicc) pip install --no-cache-dir --no-binary=mpi4py mpi4py
```

The job script must load the same modules before `conda activate`.
