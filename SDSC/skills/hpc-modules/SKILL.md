---
name: hpc-modules
description: >
  Use this skill whenever an HPC cluster user wants to use, load, find or
  check for software ("I need gromacs", "which CUDA should I use", "is LAMMPS
  installed", "load python"), needs the module lines for a job script or for
  compiling and linking, or hits an environment-modules error such as
  "module: command not found", "cannot be loaded as requested", "Unable to
  locate a modulefile", or a compiler/MPI/stack conflict. Works with Lmod and
  Tcl Environment Modules on any site.
license: MIT
compatibility: opencode
metadata:
  author: Yash Parikh
  updated: "2026-10-12"
  version: 0.1.0
  status: draft (docs-only; generic twin of expanse-modules; Environment Modules path untested)
---

## Overview

Most clusters use **Lmod**; the rest use Tcl **Environment Modules** (4.x/5.x).
Both share `avail`, `load`, `purge`, `list`, `show`, `save`/`restore`. Many sites
use a hierarchy (Core → compiler → MPI), so most packages are hidden from
`module avail` until their prerequisites are loaded. Only `module spider`
sees everything (Lmod; Environment Modules **≥ 5.6** only).

- Your shell tool is non-interactive, so `module` may be undefined. Step 1
  makes it available; reuse the same prefix in every later call.
- Module output goes to **stderr**: always append `2>&1`.
- GPU vs CPU builds differ by site: a separate stack module (`gpu`/`cpu`), a
  `-CUDA-x.y.z` version suffix (EasyBuild), or a `craype-accel-*` module (Cray).
  **Never mix modules from two prerequisite lines, compilers or stacks.**
- `module purge` may remove site defaults (scheduler, stack); sticky modules
  survive it on Lmod. Never suggest `module --force purge`.

Your commands can't change the user's shell. Print a load line or block for
the user to run. **Never edit or write the user's files.**

## Procedure

1. **Detect and find (shell call 1).** Make `module` work, identify the
   implementation, and search in one call (replace NAME):

   ```bash
   type module >/dev/null 2>&1 || for f in "$LMOD_PKG/init/bash" "$MODULESHOME/init/bash" /etc/profile.d/z00_lmod.sh /etc/profile.d/lmod.sh /etc/profile.d/modules.sh /usr/share/lmod/lmod/init/bash /usr/share/Modules/init/bash; do [ -r "$f" ] && . "$f" && break; done; type module >/dev/null 2>&1 || echo "NO MODULE CMD"; echo "LMOD=${LMOD_VERSION:-${LMOD_CMD:+yes}} ENVMOD=${MODULES_CMD:+yes}"; module --version 2>&1 | head -2; module -t list 2>&1; module spider NAME 2>&1 | head -40 || module -t avail NAME 2>&1
   ```

   - `NO MODULE CMD` → rerun every command as `bash -l -c '...'`.
   - Environment Modules < 5.6 has no spider: use `module -i -t avail NAME 2>&1`
     and see [references/envmodules.md](references/envmodules.md).
   - Nothing found → `module -r spider -i 'NAME' 2>&1` (Lmod), then
     [references/aliases.md](references/aliases.md). Still nothing → say so
     plainly and offer that file's fallbacks. **Never invent a module name or version.**

2. **Get prerequisites (shell call 2).** For the versions that matter:
   `module spider NAME/VER 2>&1`. Lmod prints "You will need to load all
   module(s) on any one of the lines below": load **every module on one line**.
   "can be loaded directly" means no prerequisites. On Environment Modules,
   read `(via X)` in spider output, or `prereq` lines in `module show NAME/VER 2>&1`.

3. **Pick the variant and version.**
   - Variant: if CPU and GPU builds both exist and the user hasn't said where
     it runs, **ask one question:** "Will this run on CPU nodes or GPU nodes?"
   - Version: the user's version/constraint, else the site default (`(D)` on
     Lmod, `(default)` on Environment Modules); pin what `module list` reports.
   - Several prerequisite lines fit → prefer the compiler/MPI the user already
     uses (job script or `module list`); else the GCC-based line.

4. **Dry-run (shell call 3).** Prove the line loads before you hand it over:

   ```bash
   module purge 2>&1; module load PREREQ_LINE NAME/VER 2>&1 && module list 2>&1; command -v sbatch srun 2>&1
   ```

   If `module purge` dropped the scheduler or a site default (sbatch missing,
   fewer modules than in step 1), re-add it before the line, or use
   `module reset` (Lmod; Environment Modules ≥ 5.2). On failure, match the
   error in [references/module-errors.md](references/module-errors.md), fix,
   and retry **once**. If it fails again, show the error and stop.

5. **Answer** in this order:
   1. One line naming what you chose, and why (default / requested / matched compiler). Mention newer versions if they exist.
   2. The interactive one-liner with pinned versions:
      `module purge && module load <site defaults you re-added> PREREQ/<ver> NAME/<ver>`
   3. The batch-script block (the script must start with `#!/bin/bash`, or `module` may be undefined):

      ```bash
      module purge
      module load <site defaults you re-added>
      module load PREREQ/<ver> ...
      module load NAME/<ver>
      module list
      ```

   4. Only if they compile or link: the relevant variables from
      `module show NAME/<ver> 2>&1` (for example `*_HOME`, `*_ROOT`, `CPATH`, `LIBRARY_PATH`).
   5. Only if they reuse this set interactively: `module save <name>` / `module restore <name>`
      (not in job scripts: saved collections break when the site moves modules).

## Guidelines

- Pin versions for every module except site defaults the site says to load unversioned; defaults change when the site updates.
- If the user pasted a job script, say which existing `module` lines to replace with the block.
- On Cray systems, change compilers with `module swap PrgEnv-a PrgEnv-b`, not purge + load.
- If the site has its own docs page on modules, point to it; site rules override this skill.
- Full sbatch scripts are the `slurm` skill's job. This skill supplies the module block only.

## Guardrails

- Every module name and version you print must come from spider/avail output in this session.
- Don't run builds, `pip install`, or the user's program on the login node.
- Don't edit `~/.bashrc` or any of the user's files. If they want modules at login, show the lines to add themselves.
- Never suggest `--force` (purge or load) unless the user asks after you explain the risk.

## References

- [references/aliases.md](references/aliases.md): user wording → module names (Spack, EasyBuild, Cray); what to do when there is no module.
- [references/module-errors.md](references/module-errors.md): Lmod and Environment Modules errors → cause → fix.
- [references/envmodules.md](references/envmodules.md): Environment Modules command differences by version.
- Lmod user guide: https://lmod.readthedocs.io/en/latest/010_user.html
- Environment Modules `module(1)`: https://modules.readthedocs.io/en/latest/module.html
