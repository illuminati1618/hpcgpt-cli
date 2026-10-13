# Module errors → cause → fix

Read this when a `module` command fails or the user pastes a module error. "Lmod" / "EM" = Environment Modules.

| Message (substring) | Cause | Fix |
|---|---|---|
| `module: command not found` / `module: Command not found.` | Non-login shell or script; `module` is a shell function that wasn't defined | Source the init file (step 1 loop), or `bash -l -c`; batch scripts must start with `#!/bin/bash` (`#!/bin/sh` doesn't get `module`). |
| `exist but cannot be loaded as requested` (Lmod) | Hierarchy: prerequisites (compiler/MPI/stack) not loaded | `module spider NAME/<ver> 2>&1`, then load every module on one of its lines first. |
| `The following module(s) are unknown` / `No module(s) or extension(s) found` (Lmod) | Wrong name or version, or not in this MODULEPATH | Check with `module spider` (case-insensitive) and the alias table. |
| `ERROR: Unable to locate a modulefile for` (EM) | Wrong name, MODULEPATH not set up, or a stale path | `module -i -t avail NAME 2>&1`; open a fresh shell; for user Spack trees, re-run `module use`. |
| `ERROR: Module cannot be loaded due to a conflict` (EM) / `Lmod is automatically replacing "A" with "B"` (Lmod) | Two compilers, MPIs, stacks or versions of one family | `module purge`, then load one consistent line. Lmod's auto-replace is a notice, not an error, unless the user pinned A. |
| `ERROR: Load of requirement X failed` (EM) | A prerequisite can't load (conflict or missing) | Load the prerequisite explicitly first and read its error. |
| `The following have been reloaded with a version change` / `Due to MODULEPATH changes ... reloaded` (Lmod) | Loading a module swapped a dependency | Usually fine; if the user pinned the dependency, load in prerequisite order. |
| `ERROR: Unload of sticky module skipped` (EM ≥ 5.4) | `module purge` hit a sticky site module | Expected; leave it. Don't use `--force`. |
| `sbatch`/`srun: command not found` after `module purge` | The purge also unloaded the scheduler or site defaults | `module reset` (Lmod; EM ≥ 5.2) or re-load the module step 1 showed (e.g. `slurm`). |
| `Lmod Warning: ... MODULEPATH has changed: please rebuild your saved collection` / `No collection named "default"` | Saved collection older than a site stack change, or missing | Load the modules again and `module save <name>`. |
| `error while loading shared libraries: libXXX.so` at run time | Built with one module set, run with another | Use the same load block in the job script as for the build. |
| Package not shown by `module avail` | Hierarchy hides it until prerequisites are loaded | Use `module spider`. |
| Stale or missing results after `module use` (Lmod) | Spider cache is out of date | Retry with `module --ignore_cache spider NAME 2>&1`. |
