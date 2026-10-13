# Environment Modules (Tcl) differences

Read this when step 1 shows Environment Modules (`MODULES_CMD` set, or `module --version` prints `Modules`)
instead of Lmod. Feature availability by version (from the Modules changelog):

| Intent | Lmod | Environment Modules |
|---|---|---|
| Find everywhere, hierarchy-aware | `module spider NAME` | `module spider NAME` (**≥ 5.6**); older: `module -t avail NAME` |
| Prerequisites for one version | `module spider NAME/VER` | `spider` shows `(via X)` (≥ 5.6); older: `module show NAME/VER` and read `prereq` lines |
| Keyword search | `module keyword WORD` | `module search WORD` / `module apropos WORD` (≥ 4.0) |
| Case-insensitive | default | `module -i avail NAME` (≥ 4.4) |
| Regex | `module -r spider 'regex'` | none; use `-C` (contains) / `-S` (starts-with) (≥ 4.3) |
| Machine-readable | `module -t avail` | `module -t avail` or `-j` (JSON) |
| Inspect | `module show X` | `module show X` / `module display X` |
| Swap | `module swap A B` | `module switch A B` |
| Back to site defaults | `module reset` / `module restore` | `module reset` (≥ 5.2) |
| Collections | `save`/`restore`/`savelist` | same (≥ 4.0) |
| Shorthand | `ml` | `ml` (≥ 4.5) |
| Default marker | `(D)` | `(default)`; aliases marked `@` |

- Since 5.0, prerequisites and conflicts are resolved automatically (`Loading requirement: X` lines).
- Version 3.2.x (old C implementation) lacks everything dated ≥ 4.0 above; use `module avail` and `module show` only.
- `module --dumpname` prints the implementation name on Lmod ≥ 8.7.50 and EM ≥ 5.6.
