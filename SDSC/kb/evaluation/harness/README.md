---
origin: kb
title: "skilleval: run and score skill studies with headless OpenCode"
author: Yash Parikh (illuminati1618)
updated: 2026-11-08
verified: docs-only
sources:
  - opencode-v1-cli
  - opencode-v1-permissions
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). How to run [skilleval.py](skilleval.py) on a laptop, in the minihpc rehearsal container, and on Expanse. Container runs were tested on 2026-11-08 (laptop runs on 2026-10-26, before the workspace change); Expanse runs haven't been tried yet.

# skilleval

`skilleval.py` (Python 3.11+, standard library only) runs a study defined by a `study.toml` (arms, model,
OpenCode version, bash policy) and a `questions.toml`. It runs every question × arm × repeat through
`opencode run --format json` and scores the event logs. Study 1: [../study-1-protocol.md](../study-1-protocol.md).

```text
skilleval.py check-arms STUDY.toml --out OUT [--probe]   # build each arm's pack, check its skill list (+ "OK" probe)
skilleval.py run        STUDY.toml --out OUT [--arms A,B] [--questions Q1,Q2] [--repeats N]
skilleval.py score      OUT --study STUDY.toml            # OUT/runs.csv, OUT/summary.md, runs/*/answer.md
```

Everything is kept in `OUT`, so a batch can be audited and re-graded later (including step by step from the
full transcripts):

| Path | What |
|---|---|
| `logs/<stamp>-<cmd>.log` | console output of each invocation |
| `logs/<stamp>-<cmd>.env.json` | environment record: command line, harness SHA-256, repo commit and dirty files, OpenCode version, container and image IDs, and the target's OS, loaded modules, conda and Slurm |
| `study/<stamp>/` | the `study.toml` and questions file as used (a warning is printed if they changed since the last invocation) |
| `packs/<arm>/` | each arm's pack, with `PROVENANCE.json` |
| `check-arms/<stamp>/<arm>/` | `opencode debug skill` output, probe transcript, OpenCode state |
| `runs/<question>-<arm>-r<n>/` | `events.jsonl` (raw OpenCode output), `stderr.txt`, `meta.json` (exit code, wall time, model, OpenCode version, host, the commit of every skill), `xdg/` (OpenCode's own session database and logs; the plugin `node_modules` it installs are dropped, their lock file kept) and, after scoring, `answer.md` |
| `runs-failed/` | earlier attempts of runs that were re-run (never deleted, not scored) |
| `runs.csv`, `summary.md` | scores |

`run` skips runs that already finished, so it can be resumed. Results contain the user's paths and host
names: keep `OUT` in a private place (not in this repository), and don't keep it in `/tmp`.

The API key comes from the environment (`NRP_LLM_API_KEY`) and is never written to disk by the harness. The
agent is allowed to run `env`, so key values are masked (`*`) in everything saved. In `--docker` mode the
key is passed to `docker exec` by name.

### The workspace

OpenCode runs against a small workspace (`--ws`, default `OUT/ws`) that holds only the current run: the
arm's pack in `cfg/`, a fresh `state/` (moved into the run's `xdg/` afterwards), the shared provider cache in
and `cache/`. OpenCode starts in the home directory (the `--home` dir if given), like a login shell. Other arms' packs, earlier runs, reference answers and scores stay outside it, so the
agent can't read them. `ws/` itself is scratch and can be deleted after a batch. Timeouts are enforced where
OpenCode runs (`timeout` inside the container in `--docker` mode), so a timed-out run can't keep running (start the container with `--init`, so killed processes are reaped).

## What each arm's pack is

`SDSC/` at the study's `base_ref` (via `git archive`, so uncommitted edits never leak in), with:

- `skills/` reduced to `base_skills` plus the arm's skills, each extracted from its own pinned commit;
- the study's model as the default (`model`, `enabled_providers`, and the agent file's `model:`);
- the agent file's `bash: ask` replaced by the study's bash policy (headless runs auto-reject `ask`).

Runs use `--agent hpcGPT`: without it OpenCode selects a bare agent with no SDSC prompt
([known-issues A0](../../hpcgpt-cli/known-issues.md)). Each run gets fresh OpenCode config/data/state
directories; the provider-package cache is shared in `OUT/.xdg-cache`.

## Laptop (harness smoke test)

```bash
npm install --prefix ~/.cache/opencode-1.18.32 opencode-ai@1.18.32
OC=~/.cache/opencode-1.18.32/node_modules/.bin/opencode
set -a; . ./.env; set +a                           # NRP_LLM_API_KEY=...
OUT=~/skilleval-results/laptop; mkdir -p "$OUT/home"   # empty HOME: no personal skills or conda leak in
H=SDSC/kb/evaluation/harness/skilleval.py; S=SDSC/kb/evaluation/study-1/study.toml
python3 $H check-arms $S --out "$OUT" --opencode "$OC" --home "$OUT/home" --probe
python3 $H run        $S --out "$OUT" --opencode "$OC" --home "$OUT/home" --repeats 1
python3 $H score "$OUT" --study $S
```

With `--home`, the harness also drops `CONDA_*` variables and conda directories from `PATH`, so the agent
doesn't find your own conda. There's no module system on a laptop, so answers are mostly "I can't find it";
this only proves the plumbing.

## minihpc container (rehearsal)

Rehearsals run in [minihpc](https://github.com/illuminati1618/minihpc)'s `expanse-like` profile: a Docker
login node with Lmod and Expanse-style `cpu`/`gpu` stacks (`gcc` → `openmpi` → `gromacs`), the `slurm`
module and its client commands (no scheduler), `cpu` + `slurm` loaded at login, and Miniforge with
`conda init` and one env on Lustre-style scratch. (The repository is private for now; ask for access.)
OpenCode is started through a login shell (`bash -lc`) in the container user's home, so the agent inherits
the module environment, as on a login node.

Only the workspace is mounted, at a neutral path inside the container; `OUT` stays on the host.

```bash
git clone https://github.com/illuminati1618/minihpc
make -C minihpc build NPM_PACKAGES=opencode-ai@1.18.32
OUT=~/skilleval-results/rehearsal; WS=~/skilleval-ws/rehearsal; mkdir -p "$OUT" "$WS"
docker run -d --init --name minihpc-expanse-like -v "$WS":/home/user/.hpcgpt minihpc-expanse-like
H=SDSC/kb/evaluation/harness/skilleval.py; S=SDSC/kb/evaluation/study-1/study.toml
D="--docker minihpc-expanse-like --ws $WS --docker-ws /home/user/.hpcgpt --note minihpc=$(git -C minihpc rev-parse HEAD)"
python3 $H check-arms $S --out "$OUT" $D --probe
python3 $H run        $S --out "$OUT" $D --repeats 1
python3 $H score "$OUT" --study $S
docker rm -f minihpc-expanse-like
```

Packs are built on the host and copied into the workspace one run at a time, so the repository itself isn't
mounted. Module versions and paths in the profile are representative, so rehearsal answers say nothing about
Expanse.

## Expanse

Same as the laptop, without `--home` (the agent should see your real environment) and with OpenCode
1.18.32 installed in your home. Run from a login node. Check `check-arms` output for unexpected skills
first: OpenCode also loads skills from `~/.claude/skills` and `~/.agents/skills`. The agent can read your
home directory on Expanse, so keep `OUT` (it holds the study files and earlier runs) somewhere it won't go
looking, or copy results off after each batch.
