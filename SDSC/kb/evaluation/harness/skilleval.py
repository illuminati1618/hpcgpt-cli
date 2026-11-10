#!/usr/bin/env python3
"""Run a skill study (arms x questions x repeats) through headless OpenCode and score the runs.

Standard library only (Python 3.11+). Run from anywhere inside an hpcgpt-cli checkout.

    skilleval.py check-arms STUDY.toml --out OUT [--probe]     # build each arm's pack, verify its skill set
    skilleval.py run        STUDY.toml --out OUT [--arms A,B] [--questions Q1] [--repeats 1]
    skilleval.py score      OUT                                 # OUT/runs.csv + OUT/summary.md

Options for check-arms and run:
    --opencode BIN       OpenCode binary (default: `opencode` on PATH); its version must match the study
    --home DIR           run OpenCode with HOME=DIR (an empty dir isolates the run from ~/.claude/skills etc.)
    --ws DIR             workspace with only the current run's pack and state (default OUT/ws)
    --docker CONTAINER   run OpenCode inside this running container via `docker exec`
    --docker-ws PATH     where --ws is bind-mounted inside that container (see README.md)
    --note KEY=VALUE     extra provenance for the environment record (repeatable)

Everything is kept in OUT: logs/ (console log + environment record per invocation), study/ (the study and
question files as used), packs/, check-arms/, runs/ (one dir per run, with OpenCode's own state in xdg/),
runs-failed/ (earlier attempts of runs that were re-run). API key values are masked in everything saved.

Every arm's pack is SDSC/ at the study's `base_ref`, with its skills/ reduced to `base_skills` plus the arm's
skills (each taken from its own pinned commit), the model set, and the eval bash policy written into the
agent file. Needs NRP_LLM_API_KEY (or the provider's key) in the environment; it is never written to disk.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import random
import re
import shutil
import socket
import sqlite3
import statistics
import subprocess
import sys
import tarfile
import time
import tomllib
from pathlib import Path

KEY_VARS = ("NRP_LLM_API_KEY", "TRITON_AI_API_KEY")


# ----------------------------------------------------------------------------- study + pack

def load_study(path: Path) -> dict:
    study = tomllib.loads(path.read_text())
    study["_dir"] = path.parent.resolve()
    qfile = study["_dir"] / study["study"]["questions"]
    study["_questions"] = {q["id"]: q for q in tomllib.loads(qfile.read_text())["questions"]}
    return study


def repo_root(start: Path) -> Path:
    out = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, check=True)
    return Path(out.stdout.strip())


def git_extract(repo: Path, ref: str, path: str, dest: Path) -> str:
    """Extract `path` at `ref` into dest (keeping the path); return the resolved commit SHA."""
    sha = subprocess.run(["git", "-C", str(repo), "rev-parse", f"{ref}^{{commit}}"],
                         capture_output=True, text=True, check=True).stdout.strip()
    data = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", sha, path],
                          capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(dest, filter="data")
    return sha


def yaml_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def patch_agent(text: str, model: str, permission: dict) -> str:
    """Set the agent's model and replace `bash: ask` with the eval policy (frontmatter is plain YAML)."""
    text, n = re.subn(r"^model:\s*.*$", f"model: {model}", text, count=1, flags=re.M)
    if n != 1:
        sys.exit("agent file has no `model:` line")
    bash = permission.get("bash", {})
    block = "  bash:\n" + "".join(f"    {yaml_quote(k)}: {v}\n" for k, v in bash.items())
    text, n = re.subn(r"^  bash:\s*\S+\s*\n", block, text, count=1, flags=re.M)
    if n != 1:
        sys.exit("agent file has no `  bash: <action>` permission line")
    extra = "".join(f"  {k}: {v}\n" for k, v in permission.items() if k != "bash" and isinstance(v, str))
    return text.replace(block, block + extra, 1)


def patch_config(text: str, model: str) -> str:
    """Make `model` the default and make sure its provider is enabled (JSONC: edit textually)."""
    provider = model.split("/", 1)[0]
    m = re.search(r'"enabled_providers"\s*:\s*\[([^\]]*)\]', text)
    if m:
        items = re.findall(r'"([^"]+)"', m.group(1))
        if provider not in items:
            items.insert(0, provider)
        text = text[: m.start()] + '"enabled_providers": [' + ", ".join(f'"{x}"' for x in items) + "]" + text[m.end():]
    text, n = re.subn(r'(^\s*"model"\s*:\s*)"[^"]*"', rf'\1"{model}"', text, count=1, flags=re.M)
    if n != 1:
        sys.exit('could not find top-level "model" in opencode.jsonc')
    return text


def build_pack(study: dict, arm: str, dest: Path) -> dict:
    """Build the config dir for one arm. Returns provenance (SHAs, skills)."""
    s = study["study"]
    repo = repo_root(study["_dir"])
    if dest.exists():
        shutil.rmtree(dest)
    tmp = dest.with_name(dest.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    base_sha = git_extract(repo, s["base_ref"], "SDSC", tmp)
    shutil.move(str(tmp / "SDSC"), dest)
    shutil.rmtree(tmp)
    shutil.rmtree(dest / "kb", ignore_errors=True)  # docs, not config

    skills_dir = dest / "skills"
    keep = set(s.get("base_skills", []))
    for d in list(skills_dir.iterdir()):
        if d.is_dir() and d.name not in keep:
            shutil.rmtree(d)
    prov = {"arm": arm, "base_sha": base_sha, "skills": {}}
    for name in sorted(keep):
        if not (skills_dir / name / "SKILL.md").exists():
            sys.exit(f"base skill {name} not found at {s['base_ref']}")
        prov["skills"][name] = base_sha
    for sk in study["arms"][arm]["skills"]:
        tmp.mkdir()
        sha = git_extract(repo, sk["ref"], f"SDSC/skills/{sk['name']}", tmp)
        shutil.move(str(tmp / "SDSC" / "skills" / sk["name"]), skills_dir / sk["name"])
        shutil.rmtree(tmp)
        prov["skills"][sk["name"]] = sha

    cfg = dest / "opencode.jsonc"
    cfg.write_text(patch_config(cfg.read_text(), s["model"]))
    agent = dest / "agents" / "hpcgpt.md"
    agent.write_text(patch_agent(agent.read_text(), s["model"], study.get("permission", {})))
    (dest / "PROVENANCE.json").write_text(json.dumps(prov, indent=2) + "\n")
    return prov


# ----------------------------------------------------------------------------- keeping everything

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def secret_values() -> list[str]:
    return [os.environ[k] for k in KEY_VARS if len(os.environ.get(k, "")) >= 8]


def redact(text: str) -> str:
    """Mask API key values (the agent may run `env`); same length, so binary files stay valid."""
    for v in secret_values():
        text = text.replace(v, "*" * len(v))
    return text


def redact_tree(root: Path) -> None:
    vals = [v.encode() for v in secret_values()]
    if not vals or not root.exists():
        return
    for f in root.rglob("*"):
        if f.is_file() and not f.is_symlink():
            data = f.read_bytes()
            if any(v in data for v in vals):
                for v in vals:
                    data = data.replace(v, b"*" * len(v))
                f.write_bytes(data)


class Tee(io.TextIOBase):
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s: str) -> int:
        for st in self.streams:
            st.write(s)
            st.flush()
        return len(s)


def start_log(out: Path, cmd: str) -> str:
    """Copy everything printed to OUT/logs/<stamp>-<cmd>.log; return the stamp."""
    stamp = time.strftime("%Y%m%dT%H%M%S")
    (out / "logs").mkdir(parents=True, exist_ok=True)
    sys.stdout = Tee(sys.__stdout__, open(out / "logs" / f"{stamp}-{cmd}.log", "a"))
    return stamp


def snapshot_study(study: dict, study_path: Path, out: Path, stamp: str) -> dict:
    """Copy study.toml + questions as used into OUT/study/<stamp>/; warn if they changed since the last copy."""
    files = [study_path.resolve(), study["_dir"] / study["study"]["questions"]]
    hashes = {f.name: sha256(f) for f in files}
    snaps = sorted(d for d in (out / "study").glob("*") if d.is_dir()) if (out / "study").exists() else []
    if snaps:
        prev = {f.name: sha256(f) for f in snaps[-1].iterdir() if f.is_file()}
        if prev != hashes:
            print(f"WARNING: study files differ from the snapshot in {snaps[-1].name}; runs in OUT now mix versions")
    dest = out / "study" / stamp
    dest.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.copy2(f, dest / f.name)
    return hashes


# ----------------------------------------------------------------------------- running opencode

class Runner:
    """Runs OpenCode against a small workspace (WS) holding only the current run's pack and state.

    WS/cfg   the arm's pack (copied in before each run)      WS/state  XDG config/data/state of the run
    WS/cache shared XDG cache (provider packages)

    OpenCode starts in $HOME (the --home dir if given; the container user's home with --docker).

    Results, other arms' packs, earlier runs and the study files stay in OUT, outside WS, so the agent
    under test can't read them. With --docker, WS is bind-mounted into the container at --docker-ws.
    """

    def __init__(self, a: argparse.Namespace, out: Path):
        self.bin = a.opencode
        self.docker = a.docker
        self.home = Path(a.home).resolve() if a.home else None
        self.ws = Path(a.ws).resolve() if a.ws else out / "ws"
        if self.ws == out or self.ws in [out / d for d in ("runs", "runs-failed", "packs", "study", "logs")]:
            sys.exit("--ws must be its own directory, not OUT or one of its result folders")
        if self.docker and not a.docker_ws:
            sys.exit("--docker needs --docker-ws: the absolute path where WS is mounted inside the container")
        self.seen = a.docker_ws.rstrip("/") if self.docker else str(self.ws)  # WS as OpenCode sees it
        for d in ("cfg", "state", "cache"):
            (self.ws / d).mkdir(parents=True, exist_ok=True)

    def env(self) -> dict:
        w = self.seen
        env = {
            "OPENCODE_CONFIG_DIR": f"{w}/cfg",
            "OPENCODE_TUI_CONFIG": f"{w}/cfg/tui.jsonc",
            "XDG_CONFIG_HOME": f"{w}/state/config",
            "XDG_DATA_HOME": f"{w}/state/data",
            "XDG_STATE_HOME": f"{w}/state/state",
            "XDG_CACHE_HOME": f"{w}/cache",
        }
        if self.home:
            env["HOME"] = str(self.home)
        return env

    def stage(self, pack: Path) -> None:
        """Fresh state, and this arm's pack (only) in WS/cfg."""
        for d in ("cfg", "state"):
            shutil.rmtree(self.ws / d, ignore_errors=True)
        shutil.copytree(pack, self.ws / "cfg")
        for d in ("config", "data", "state"):
            (self.ws / "state" / d).mkdir(parents=True)

    def collect(self, dest: Path) -> None:
        """Move the run's OpenCode state (session store, logs) out of WS into dest, keys masked."""
        if (self.ws / "state").exists():
            shutil.move(str(self.ws / "state"), dest)
            # OpenCode installs its plugin dependencies into every fresh config dir (~64 MB); keep only the
            # package.json/package-lock.json that pin them
            for nm in list(dest.rglob("node_modules")):
                if nm.is_dir():
                    shutil.rmtree(nm)
            for db in dest.rglob("*.db"):  # fold the write-ahead log into the database file
                try:
                    con = sqlite3.connect(db)
                    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    con.close()
                except sqlite3.Error as e:
                    print(f"note: could not checkpoint {db}: {e}")
            redact_tree(dest)
        (self.ws / "state").mkdir()

    def local_env(self) -> dict:
        full_env = {**os.environ, **self.env()}
        if self.home:  # isolate from the caller's own conda as well as their dotfiles
            full_env = {k: v for k, v in full_env.items() if not k.startswith(("CONDA_", "_CE_", "MAMBA_"))}
            full_env["PATH"] = os.pathsep.join(
                d for d in full_env.get("PATH", "").split(os.pathsep) if "conda" not in d and "forge" not in d)
        for k in KEY_VARS:
            full_env.setdefault(k, "unset")
        return full_env

    def docker_prefix(self) -> list[str]:
        cmd = ["docker", "exec", "-i"]
        for k, v in self.env().items():
            cmd += ["-e", f"{k}={v}"]
        for k in KEY_VARS:  # passed by name: docker reads the value from our environment
            if k in os.environ:
                cmd += ["-e", k]
        return cmd + [self.docker]

    def run(self, args: list[str], timeout: int) -> tuple[str, str, int | str]:
        """Run OpenCode with `timeout` enforced where it runs (inside the container in docker mode)."""
        if self.docker:
            # a login shell in $HOME, like a user on a login node: profile.d sets up modules, ~/.bashrc conda
            cmd = self.docker_prefix() + ["bash", "-lc", 'cd ~ && exec timeout -k 10 "$0" "$@"',
                                          str(timeout), self.bin, *args]
            env, cwd = os.environ, None
        else:
            cmd = ["timeout", "-k", "10", str(timeout), self.bin, *args]
            env, cwd = self.local_env(), self.home or Path.home()  # start in $HOME, like a login shell
        try:
            t0 = time.time()
            r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                               timeout=timeout + 60, stdin=subprocess.DEVNULL)
            # 124: stopped by `timeout`; 137: it ignored SIGTERM and was killed 10 s later
            hit = r.returncode == 124 or (r.returncode == 137 and time.time() - t0 >= timeout)
            code: int | str = "timeout" if hit else r.returncode
            return redact(r.stdout), redact(r.stderr), code
        except subprocess.TimeoutExpired as e:
            dec = lambda b: (b.decode(errors="replace") if isinstance(b, bytes) else (b or ""))
            return redact(dec(e.stdout)), redact(dec(e.stderr)), "timeout"

    def shell(self, script: str) -> str:
        """Run a shell snippet where the agent runs (login shell), for the environment record."""
        wrapped = "{ " + script + "; } 2>&1"
        if self.docker:
            cmd = self.docker_prefix() + ["bash", "-lc", "cd ~ && " + wrapped]
            env, cwd = os.environ, None
        else:
            cmd = ["bash", "-lc", wrapped]
            env, cwd = self.local_env(), self.home or Path.home()  # start in $HOME, like a login shell
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=300,
                           stdin=subprocess.DEVNULL)
        return redact(r.stdout + r.stderr)

    def version(self) -> str:
        out, err, _ = self.run(["--version"], 120)
        return out.strip()


ENV_SCRIPT = ("echo '# os-release'; cat /etc/os-release; echo '# uname'; uname -a; echo '# user'; id; "
              "echo '# modules'; module -t list; echo '# avail (first 80)'; module -t avail 2>&1 | head -80; "
              "echo '# conda'; command -v conda && conda --version; echo '# slurm'; command -v sbatch sinfo; "
              "echo '# disk'; df -h ~")


def record_env(a: argparse.Namespace, runner: Runner, study_path: Path, out: Path, stamp: str,
               hashes: dict, version: str) -> None:
    """OUT/logs/<stamp>-<cmd>.env.json: everything needed to tell later what this invocation ran on."""
    repo = repo_root(study_path.parent)
    git = lambda *x: subprocess.run(["git", "-C", str(repo), *x], capture_output=True, text=True).stdout.strip()
    info = {
        "argv": sys.argv, "stamp": stamp, "cwd": os.getcwd(), "python": sys.version, "host": socket.gethostname(),
        "uname": " ".join(os.uname()), "harness": str(Path(__file__).resolve()),
        "harness_sha256": sha256(Path(__file__).resolve()),
        "repo_head": git("rev-parse", "HEAD"), "repo_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "repo_status": git("status", "--porcelain"), "study_files_sha256": hashes,
        "opencode_bin": runner.bin, "opencode_version": version,
        "ws": str(runner.ws), "ws_as_seen": runner.seen, "home": str(runner.home or ""),
        "notes": dict(n.split("=", 1) for n in (a.note or [])),
    }
    if runner.docker:
        insp = subprocess.run(["docker", "inspect", runner.docker], capture_output=True, text=True)
        try:
            c = json.loads(insp.stdout)[0]
            info["docker_container"] = {"name": runner.docker, "id": c["Id"], "image_id": c["Image"],
                                        "image": c["Config"]["Image"], "created": c["Created"],
                                        "mounts": c.get("Mounts", [])}
        except (ValueError, IndexError, KeyError):
            info["docker_container"] = {"name": runner.docker, "inspect_error": insp.stderr}
        info["docker_version"] = subprocess.run(["docker", "version", "--format", "{{json .}}"],
                                                capture_output=True, text=True).stdout.strip()
    info["target_environment"] = runner.shell(ENV_SCRIPT)
    (out / "logs" / f"{stamp}-{a.cmd}.env.json").write_text(json.dumps(info, indent=2) + "\n")


def first_json(text: str):
    i = min([p for p in (text.find("["), text.find("{")) if p >= 0], default=-1)
    if i < 0:
        raise ValueError("no JSON in output")
    return json.JSONDecoder().raw_decode(text[i:])[0]


def prepare(a: argparse.Namespace, study: dict, out: Path, arms: list[str]) -> tuple[Runner, dict, str]:
    out.mkdir(parents=True, exist_ok=True)
    stamp = start_log(out, a.cmd)
    print(f"# {a.cmd} {stamp}: {' '.join(sys.argv)}")
    hashes = snapshot_study(study, Path(a.study), out, stamp)
    runner = Runner(a, out)
    want = study["study"]["opencode_version"]
    got = runner.version()
    record_env(a, runner, Path(a.study), out, stamp, hashes, got)
    if got != want:
        sys.exit(f"OpenCode version {got!r} != study's {want!r} (use --opencode)")
    packs = {}
    for arm in arms:
        packs[arm] = build_pack(study, arm, out / "packs" / arm)
    return runner, packs, stamp


def cmd_check_arms(a: argparse.Namespace) -> int:
    study = load_study(Path(a.study))
    out = Path(a.out).resolve()
    arms = list(study["arms"])
    runner, packs, stamp = prepare(a, study, out, arms)
    ok = True
    for arm in arms:
        cdir = out / "check-arms" / stamp / arm
        cdir.mkdir(parents=True, exist_ok=True)
        runner.stage(out / "packs" / arm)
        so, se, code = runner.run(["debug", "skill"], 300)
        (cdir / "debug-skill.stdout").write_text(so)
        (cdir / "debug-skill.stderr").write_text(se)
        try:
            found = sorted(x["name"] for x in first_json(so))
        except ValueError:
            print(f"[{arm}] could not parse `opencode debug skill` (exit {code}):\n{so[-2000:]}{se[-2000:]}")
            ok = False
            runner.collect(cdir / "xdg")
            continue
        expected = sorted(packs[arm]["skills"])
        extra = [x for x in found if x not in expected]
        missing = [x for x in expected if x not in found]
        # built-in skills ship with OpenCode itself and are the same in every arm
        extra_nonbuiltin = [x for x in extra if x not in ("customize-opencode",)]
        status = "OK" if not missing and not extra_nonbuiltin else "MISMATCH"
        ok &= status == "OK"
        print(f"[{arm}] {status}: skills={found}" + (f" missing={missing}" if missing else "")
              + (f" unexpected={extra_nonbuiltin}" if extra_nonbuiltin else ""))
        if a.probe:
            so, se, code = runner.run(["run", "--agent", study["study"]["agent"], "--format", "json",
                                       "Reply with just OK."], 300)
            (cdir / "probe-events.jsonl").write_text(so)
            (cdir / "probe-stderr.txt").write_text(se)
            ev = parse_events(so)
            print(f"[{arm}] probe: exit={code} input_tokens={ev['input']} agent_text={ev['answer'][:40]!r}")
        runner.collect(cdir / "xdg")
    print("check-arms:", "OK" if ok else "MISMATCH")
    return 0 if ok else 1


def cmd_run(a: argparse.Namespace) -> int:
    study = load_study(Path(a.study))
    s = study["study"]
    out = Path(a.out).resolve()
    arms = a.arms.split(",") if a.arms else list(study["arms"])
    qids = a.questions.split(",") if a.questions else list(study["_questions"])
    repeats = a.repeats or s["repeats"]
    runner, packs, stamp = prepare(a, study, out, arms)
    version = s["opencode_version"]
    plan = [(q, arm, rep) for q in qids for arm in arms for rep in range(1, repeats + 1)]
    random.Random(s.get("seed", 1)).shuffle(plan)  # interleave arms so throttling/time of day don't bias one
    print(f"{len(plan)} runs -> {out / 'runs'}")
    for i, (qid, arm, rep) in enumerate(plan, 1):
        run_id = f"{qid}-{arm}-r{rep}"
        rdir = out / "runs" / run_id
        meta_path = rdir / "meta.json"
        if meta_path.exists() and json.loads(meta_path.read_text()).get("exit") == 0:
            print(f"[{i}/{len(plan)}] {run_id} done, skipping")
            continue
        if rdir.exists():  # an earlier failed/aborted attempt: keep it, out of the way of scoring
            kept = out / "runs-failed" / f"{run_id}-{stamp}"
            kept.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(rdir), kept)
            print(f"[{i}/{len(plan)}] {run_id}: earlier attempt moved to {kept.relative_to(out)}")
        rdir.mkdir(parents=True)
        q = study["_questions"][qid]
        args = ["run", "--agent", s["agent"], "--format", "json", q["prompt"]]
        runner.stage(out / "packs" / arm)
        t0 = time.time()
        stdout, stderr, code = runner.run(args, s.get("timeout_s", 600))
        wall = time.time() - t0
        (rdir / "events.jsonl").write_text(stdout)
        (rdir / "stderr.txt").write_text(stderr)
        runner.collect(rdir / "xdg")
        meta = {"run_id": run_id, "question": qid, "arm": arm, "repeat": rep, "exit": code,
                "wall_s": round(wall, 1), "started": t0, "invocation": stamp, "model": s["model"],
                "agent": s["agent"], "opencode_version": version, "study": s["id"], "study_version": s["version"],
                "host": socket.gethostname(), "docker": runner.docker, "provenance": packs[arm]}
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        ev = parse_events(stdout)
        print(f"[{i}/{len(plan)}] {run_id} exit={code} {wall:.0f}s tokens={ev['total']} "
              f"tools={ev['tool_calls']} denied={ev['denied']} skills={ev['skills_loaded']}")
    return 0


# ----------------------------------------------------------------------------- scoring

def parse_events(stdout: str) -> dict:
    ev = {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0, "total": 0, "steps": 0,
          "tool_calls": 0, "denied": 0, "tool_errors": 0, "skills_loaded": [], "bash": [], "answer": "",
          "parse_errors": 0}
    texts: dict[str, list[str]] = {}
    last_msg = None
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            ev["parse_errors"] += 1
            continue
        p = e.get("part", {})
        t = e.get("type")
        if t == "step_finish":
            tok = p.get("tokens", {})
            ev["steps"] += 1
            ev["input"] += tok.get("input", 0)
            ev["output"] += tok.get("output", 0)
            ev["reasoning"] += tok.get("reasoning", 0)
            ev["cache_read"] += tok.get("cache", {}).get("read", 0)
            ev["cache_write"] += tok.get("cache", {}).get("write", 0)
            ev["total"] += tok.get("total", 0)
        elif t == "tool_use":
            ev["tool_calls"] += 1
            st = p.get("state", {})
            inp = st.get("input", {}) or {}
            if st.get("status") == "error":
                err = str(st.get("error", "")).lower()
                if any(s in err for s in ("rejected permission", "prevents you from using", "denied")):
                    ev["denied"] += 1
                else:
                    ev["tool_errors"] += 1
            if p.get("tool") == "skill":
                ev["skills_loaded"].append(inp.get("name", "?"))
            elif p.get("tool") == "bash":
                ev["bash"].append(inp.get("command", ""))
        elif t == "text":
            mid = p.get("messageID")
            texts.setdefault(mid, []).append(p.get("text", ""))
            last_msg = mid
    ev["answer"] = "".join(texts.get(last_msg, [])) if last_msg else ""
    return ev


def apply_checks(q: dict, answer: str) -> dict:
    res = {}
    for c in q.get("checks", []):
        hit = re.search(c["pattern"], answer, re.I | re.M) is not None
        res[c["id"]] = hit if c["kind"] == "must" else not hit
    return res


def cmd_score(a: argparse.Namespace) -> int:
    out = Path(a.out).resolve()
    study = load_study(Path(a.study)) if a.study else None
    rows = []
    for meta_path in sorted((out / "runs").glob("*/meta.json")):
        meta = json.loads(meta_path.read_text())
        ev = parse_events((meta_path.parent / "events.jsonl").read_text())
        q = study["_questions"][meta["question"]] if study else {}
        checks = apply_checks(q, ev["answer"])
        expect = q.get("skills", {})
        arm_skill = {"B": expect.get("generic"), "C": expect.get("expanse")}.get(meta["arm"])
        row = {
            "run_id": meta["run_id"], "question": meta["question"], "arm": meta["arm"], "repeat": meta["repeat"],
            "exit": meta["exit"], "wall_s": meta["wall_s"],
            **{k: ev[k] for k in ("total", "input", "output", "reasoning", "cache_read", "cache_write", "steps",
                                  "tool_calls", "denied", "tool_errors", "parse_errors")},
            "skills_loaded": ";".join(ev["skills_loaded"]),
            "expected_skill_loaded": "" if not arm_skill else int(arm_skill in ev["skills_loaded"]),
            "checks_passed": sum(checks.values()), "checks_total": len(checks),
            "auto_pass": int(bool(checks) and all(checks.values()) and meta["exit"] == 0 and bool(ev["answer"])),
            "failed_checks": ";".join(k for k, v in checks.items() if not v),
            "answer_chars": len(ev["answer"]),
            # candidate "asked for clarification" (runs are single-turn); graders decide
            "asks_question": int(any(ln.rstrip(" *_").endswith("?") for ln in
                                     (lambda ls: ls[:1] + ls[-1:])(ev["answer"].strip().splitlines()))),
        }
        rows.append(row)
        (meta_path.parent / "answer.md").write_text(ev["answer"] + "\n")
    if not rows:
        print("no runs found")
        return 1
    with open(out / "runs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def agg(rs: list[dict]) -> str:
        toks = [r["total"] for r in rs]
        passed = [r for r in rs if r["auto_pass"]]
        tps = (sum(toks) / len(passed)) if passed else float("inf")
        loaded = [r["expected_skill_loaded"] for r in rs if r["expected_skill_loaded"] != ""]
        trig = f"{sum(loaded)}/{len(loaded)}" if loaded else "-"
        return (f"| {len(rs)} | {sum(r['auto_pass'] for r in rs)}/{len(rs)} | {statistics.median(toks):,.0f} | "
                f"{'inf' if tps == float('inf') else f'{tps:,.0f}'} | {statistics.mean(r['steps'] for r in rs):.1f} | "
                f"{statistics.mean(r['tool_calls'] for r in rs):.1f} | {sum(r['denied'] for r in rs)} | {trig} |")

    head = ("| runs | auto-pass | median tokens | tokens per auto-pass | mean steps | mean tool calls | denied | "
            "expected skill loaded |\n|---|---|---|---|---|---|---|---|")
    lines = ["# Results (provisional auto-checks; human grading decides pass/fail)", "",
             "## By arm", "", "| arm " + head.replace("\n|", "\n|---|", 1)]
    for arm in sorted({r["arm"] for r in rows}):
        lines.append(f"| {arm} " + agg([r for r in rows if r["arm"] == arm]))
    lines += ["", "## By question and arm", "", "| question | arm " + head.replace("\n|", "\n|---|---|", 1)]
    for qid in sorted({r["question"] for r in rows}):
        for arm in sorted({r["arm"] for r in rows}):
            rs = [r for r in rows if r["question"] == qid and r["arm"] == arm]
            if rs:
                lines.append(f"| {qid} | {arm} " + agg(rs))
    failed = sorted(d.name for d in (out / "runs-failed").glob("*")) if (out / "runs-failed").exists() else []
    lines += ["", f"Earlier failed attempts kept in runs-failed/ (not scored): {len(failed)}"]
    lines += [f"- {x}" for x in failed]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


# ----------------------------------------------------------------------------- cli

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check-arms", "run"):
        p = sub.add_parser(name)
        p.add_argument("study")
        p.add_argument("--out", required=True)
        p.add_argument("--opencode", default="opencode")
        p.add_argument("--home")
        p.add_argument("--ws", help="workspace OpenCode runs against (default OUT/ws)")
        p.add_argument("--docker")
        p.add_argument("--docker-ws", help="where --ws is mounted inside the container (absolute path)")
        p.add_argument("--note", action="append", metavar="KEY=VALUE",
                       help="extra provenance for the environment record (repeatable)")
        if name == "check-arms":
            p.add_argument("--probe", action="store_true", help="also send 'Reply with just OK.' per arm")
        else:
            p.add_argument("--arms")
            p.add_argument("--questions")
            p.add_argument("--repeats", type=int)
    p = sub.add_parser("score")
    p.add_argument("out")
    p.add_argument("--study", help="study.toml (needed for the answer checks)")
    a = ap.parse_args()
    return {"check-arms": cmd_check_arms, "run": cmd_run, "score": cmd_score}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
