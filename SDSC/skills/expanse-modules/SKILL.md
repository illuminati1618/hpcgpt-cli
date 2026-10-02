---
name: expanse-modules
description: >
  Use this skill whenever an Expanse user wants to use, load, find or check
  for software ("I need gromacs", "which CUDA should I use", "is LAMMPS
  installed", "load python"), needs the module lines for a job script or for
  compiling and linking, or hits an Lmod / `module` error such as "module:
  command not found", "cannot be loaded", or a cpu/gpu stack conflict.
license: MIT
compatibility: opencode
metadata:
  author: Yash Parikh
  updated: "2026-09-28"
  version: 0.1.0
  status: draft (docs-only; not yet tested on Expanse)
---

## Overview

Expanse uses Lmod with hierarchical Spack software stacks. Most packages are
hidden from `module avail` until their prerequisites are loaded, so a load line
has a fixed order: **stack** (`cpu` or `gpu`) → **compiler** → **MPI** (if
needed) → **package**. Only `module spider` sees everything.

- `cpu` stack: for `compute`, `shared`, `debug`, `large-shared` partitions.
- `gpu` stack: for `gpu`, `gpu-shared`, `gpu-debug`, `gpu-preempt` (V100).
- **Never load `cpu` and `gpu` together.**
- Lmod prints to **stderr**: always append `2>&1`.
- Your shell tool is non-interactive. Start every command with
  `source /etc/profile.d/modules.sh;` so `module` exists.
- Bare names in `/cm/shared/modulefiles` (e.g. `cuda10.2/toolkit`,
  `openmpi/gcc/64`) are old cluster modules outside the Spack stacks. Don't
  recommend them unless the user asks.

Your commands can't change the user's shell. Print a load line or block for
the user to run. **Never edit or write the user's files.**

## Procedure

1. **Find it (shell call 1).** Get every version and its prerequisites in one call:

   ```bash
   source /etc/profile.d/modules.sh; for m in $(module -t spider NAME 2>&1 | grep -i '^NAME/'); do echo "== $m"; module spider "$m" 2>&1 | awk '/loaded directly/{print;exit} /need to load/{f=1;next} f&&/Help:|^ *-{3,}/{exit} f&&NF'; done
   ```

   - No output → try `module -r spider -i 'NAME' 2>&1`, then
     [references/aliases.md](references/aliases.md). If it still isn't found,
     say so plainly and offer the fallbacks in that file. **Never invent a
     module name or version.**
   - Each version prints either "can be loaded directly" (no prerequisites)
     or one or more prerequisite lines like `cpu/<ver>  gcc/<ver>  openmpi/<ver>`.
     The first module on the line tells you the stack.

2. **Pick the stack.** If the package is in only one stack, use it. If it's in
   both and the user hasn't said whether it runs on CPU or GPU nodes, **ask
   one question:** "Will this run on CPU nodes or GPU nodes?"

3. **Pick the version and prerequisite line.**
   - The user gave a version or constraint → use the matching version.
   - Otherwise use the **site default**. Leave the version off in step 4, and
     Lmod resolves the default. Pin what `module list` reports.
   - If several prerequisite lines fit, prefer the compiler/MPI the user
     already uses (in their job script or `module list`). Otherwise use the
     `gcc` line.

4. **Dry-run (shell call 2).** Prove the line loads before you hand it over:

   ```bash
   source /etc/profile.d/modules.sh; module purge; module load STACK slurm COMPILER MPI NAME 2>&1 && module list 2>&1; module avail NAME 2>&1 | grep -i NAME
   ```

   On failure, match the error in
   [references/lmod-errors.md](references/lmod-errors.md), fix it, and retry
   **once**. If it fails again, show the error and stop.

5. **Answer** in this order:
   1. One line naming what you chose, and why (default / requested / matched compiler). Mention newer versions if they exist.
   2. The interactive one-liner with pinned versions (keep `slurm`, or the user loses `sbatch`/`squeue`):
      `module purge && module load STACK/<ver> slurm COMPILER/<ver> MPI/<ver> NAME/<ver>`
   3. The batch-script block:

      ```bash
      module purge
      module load STACK/<ver>
      module load slurm
      module load COMPILER/<ver> MPI/<ver>
      module load NAME/<ver>
      ```

   4. Only if they compile or link: the relevant variables from
      `module show NAME/<ver> 2>&1` (for example `*_HOME`, `*_ROOT`,
      `CPATH`, `LIBRARY_PATH`).
   5. Only if they reuse this set often: `module save <name>` /
      `module restore <name>`.

## Guidelines

- Pin versions for the stack, compiler, MPI and package; defaults change when SDSC updates a stack. Load `slurm` without a version.
- If the user pasted a job script, say which existing `module` lines to replace with the block.
- An interactive GPU session should start with `module purge; module restore`, then `module load gpu` (Expanse user guide).
- H100 (`nairr-gpu*`) software stack: unverified. Run the step 1 search, and don't assume the V100 `gpu` stack applies.
- Full sbatch scripts are the `slurm` and `expanse-gpu-request` skills' job. This skill supplies the module block only.

## Guardrails

- Every module name and version you print must come from spider/avail output in this session.
- Don't run builds, `pip install`, or the user's program on the login node.
- Don't edit `~/.bashrc` or any of the user's files. If they want modules at login, show the lines to add themselves.

## References

- [references/aliases.md](references/aliases.md): user wording → module names; what to do when there is no module.
- [references/lmod-errors.md](references/lmod-errors.md): Lmod error messages → cause → fix.
- Expanse user guide, Modules: https://www.sdsc.edu/support/user_guides/expanse.html#modules
- Lmod docs: https://lmod.readthedocs.io
