# What users say → what to search

Use this only when `module -t spider NAME` found nothing. These are search hints,
not facts: always confirm with spider before printing a name.

| User says | Try `module spider` / `module -r spider -i` | Notes |
|---|---|---|
| python, python3 | `anaconda3`, `python`, `py-` | Spack Python packages are named `py-<pkg>` (e.g. `py-numpy`). |
| numpy, scipy, mpi4py, h5py | `py-numpy`, `py-scipy`, `py-mpi4py`, `py-h5py` | Spack prefix `py-`. |
| R, Rscript | `r` | Single letter; use `module -t spider r 2>&1 \| grep -i '^r/'`. |
| cuda, nvcc, cudatoolkit | `cuda` | `gpu` stack. |
| cudnn, nccl | `cudnn`, `nccl` | `gpu` stack. |
| fftw3 | `fftw` | |
| mkl, intel-mkl | `intel-mkl`, `intel` | The `intel` compiler sets `INTEL_MKLHOME` (user guide). |
| blas, lapack | `openblas`, `intel-mkl`, `netlib-lapack` | |
| mpi, mpich | `openmpi`, `mvapich2`, `intel-mpi` | Pick the one built with the chosen compiler. |
| hdf5 / netcdf | `hdf5`, `netcdf-c`, `netcdf-fortran` | Parallel builds sit under an MPI. |
| gromacs, lammps, namd, amber, quantum espresso | `gromacs`, `lammps`, `namd`, `amber`, `quantum-espresso` | Check both stacks; GPU builds are in `gpu`. |
| matlab, abaqus, gaussian | `matlab`, `abaqus`, `gaussian` | Licensed; may need group access. |
| singularity, apptainer | `singularitypro` | |
| git, cmake | `git`, `cmake` | |

## When there is no module

Say "There is no module for X on Expanse" first, then offer the options that fit:

1. **Container**: `module load singularitypro`. SDSC provides PyTorch and
   TensorFlow images, and users can pull NGC/Docker images
   (`singularity pull docker://…`). Examples live in `/cm/shared/examples/sdsc/`.
   This is the usual answer for PyTorch, TensorFlow, JAX and vLLM.
2. **Conda/mamba in the user's space**, for Python/R stacks. Install under
   `$HOME` or project storage. Don't run large installs on the login node; use
   an interactive job.
3. **User-level Spack**, chained to the system stack, for compiled HPC
   libraries. Point to the SDSC docs; don't attempt the build yourself.
4. **Ask SDSC** to install it: consult@sdsc.edu (or the ACCESS ticket system).
