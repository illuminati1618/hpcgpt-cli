# Lmod errors → cause → fix

Read this when a `module` command fails or the user pastes an Lmod error.

| Message (substring) | Cause | Fix |
|---|---|---|
| `module: command not found` | Non-login shell or script; `module` is a shell function that wasn't inherited | Add `source /etc/profile.d/modules.sh` before any `module` line (user guide). |
| `These module(s) or extension(s) exist but cannot be loaded as requested` | Prerequisites (stack/compiler/MPI) not loaded | `module spider NAME/<ver> 2>&1` and load one full prerequisite line first, in order. |
| `The following module(s) are unknown` | Wrong name/version, or a module from the other stack | Check spelling with `module -t spider NAME`; check the `cpu` vs `gpu` stack. |
| `Lmod has detected the following error: ... conflict` / one stack swaps out the other | `cpu` and `gpu` stacks (or two compilers/MPIs) loaded together | `module purge`, then load a single consistent line. |
| `The following have been reloaded with a version change` | Loading a module swapped a dependency's version | Usually fine. If the user pinned that dependency, load in prerequisite order and pin it. |
| `srun: command not found` / `sbatch: command not found` after `module purge` | `module purge` also unloads `slurm` | Add `module load slurm` after the stack (as in the user guide's examples). |
| `Lmod Warning: The system MODULEPATH has changed: please rebuild your saved collection` | Saved collection made before a stack change | `module savelist`, `module disable <name>` (or delete `~/.lmod.d/<name>`), reload modules, `module save <name>` again. |
| `error while loading shared libraries: libXXX.so` at run time | The module was loaded at build time but not at run time, or a different stack was used | Use the same load block in the job script as for the build. |
| Package not shown by `module avail` | Normal: hierarchy hides it until the prerequisites are loaded | Use `module spider`, not `module avail`. |
