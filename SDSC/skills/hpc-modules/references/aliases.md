# What users say → what to search

Use this only when `module spider NAME` (or `module -i -t avail NAME`) found nothing. These are search
hints, not facts: always confirm with spider/avail before printing a name. Naming depends on how the site
built its software: Spack (`name/ver`, lowercase, Python packages as `py-<pkg>`, flat trees may append
`-<compiler>-<ver>-<hash>`), EasyBuild (`Name/ver-<toolchain>[-CUDA-x.y.z]`, capitalised, e.g.
`GROMACS/2024.1-foss-2023b`), or Cray PE (`PrgEnv-*`, `cray-*`).

| User says | Try | Notes |
|---|---|---|
| python, python3 | `python`, `Python`, `anaconda3`, `miniforge`, `miniconda` | Conda modules are a separate path (see the `hpc-conda` skill). |
| numpy, scipy, mpi4py, h5py | `py-numpy` (Spack), `SciPy-bundle` (EasyBuild), `mpi4py`, `h5py` | On Lmod, `module spider numpy` may list it as an extension `(E)` of another module: load that module. |
| R, Rscript | `r`, `R` | Single letter; filter: `module -t spider r 2>&1 \| grep -i '^r/'`. |
| cuda, nvcc, cudatoolkit | `cuda`, `CUDA`, `cudatoolkit`, `nvhpc` | Often only in the GPU stack, or as a `-CUDA-` suffix on packages. |
| cudnn, nccl | `cudnn`, `cuDNN`, `nccl`, `NCCL` | |
| fftw3 | `fftw`, `FFTW`, `cray-fftw` | |
| mkl, blas, lapack | `intel-oneapi-mkl`, `imkl`, `intel-mkl`, `openblas`, `OpenBLAS`, `cray-libsci`, `flexiblas` | |
| mpi, mpich | `openmpi`, `OpenMPI`, `mvapich2`, `intel-oneapi-mpi`, `impi`, `cray-mpich`, `mpich` | Pick the one built with the chosen compiler. EasyBuild `foss`/`gompi` toolchains include OpenMPI. |
| compiler, gcc, intel | `gcc`, `GCC`, `intel-oneapi-compilers`, `intel`, `nvhpc`, `aocc`, `PrgEnv-*` | |
| hdf5 / netcdf | `hdf5`, `HDF5`, `cray-hdf5`, `netcdf-c`, `netCDF`, `cray-netcdf` | Parallel builds sit under an MPI. |
| gromacs, lammps, namd, amber, quantum espresso | `gromacs`, `lammps`, `namd`, `amber`, `quantum-espresso`, `QuantumESPRESSO` | Check both CPU and GPU variants. |
| matlab, abaqus, gaussian | `matlab`, `MATLAB`, `abaqus`, `gaussian` | Licensed; may need group access. |
| singularity, apptainer, containers | `apptainer`, `singularity`, `singularitypro`, `podman` | Also check `command -v apptainer singularity` (may be installed without a module). |
| git, cmake | `git`, `cmake`, `CMake` | Often also in the OS without a module. |

## When there is no module

Say "There is no module for X on this system" first, then offer the options that fit:

1. **Container** (Apptainer/Singularity): pull an image, e.g. `apptainer pull docker://…`. Usual answer for
   PyTorch, TensorFlow, JAX and vLLM. Check the site's docs for provided images.
2. **Conda/mamba or a venv in the user's space**, for Python/R stacks (the `hpc-conda` skill). Don't run big
   installs on the login node.
3. **User-level Spack or EasyBuild**, for compiled HPC libraries; Spack modules are enabled with
   `module use $SPACK_ROOT/share/spack/modules/$(spack arch)`. Point to the docs; don't attempt the build.
4. **Ask the site's support team** to install it (their ticket system or help email).
