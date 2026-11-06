"""Track B on this machine: one headless Claude Code session per (task, arm), sandboxed.

The cloud runs started sessions through the session API. This runner starts the same
sessions with ``claude -p`` (same prompt, model and arms, from ``configs/trackb.yaml``) and
saves records where ``csbench trackb-report`` reads them, so both are scored alike.

What a session sees mirrors the cloud image: the repository at ``/home/user/<repo>``, HOME
``/home/user``, both tools on PATH in ``~/.local/bin`` (installed from the pinned lock
files). No path or variable names the benchmark, the task source or the arm.

Isolation: bubblewrap with the system read-only and /home, /tmp, /var/tmp and /run/user
replaced by empty ones, so the user's own Claude Code setup (settings, CLAUDE.md, skills,
plugins, MCP servers, hooks, memory), the gold data and other arms' files are not there. The
session signs in with the account's current OAuth access token in ``CLAUDE_CODE_OAUTH_TOKEN``:
it never sees the credentials file and cannot refresh or rotate the login. Network stays
open (the session needs the API); web tools are off.

Indexes are built before the session and timed separately (``prebuild_s``), so session time
and tokens measure using a tool, not building it. The checkout is a depth-1 fetch of the
base commit, with no remote and no later history.
"""

from __future__ import annotations

import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from csbench.dataset import Task
from csbench.trackb import session_request

WORK = Path(
    os.environ.get("CSBENCH_WORK") or Path(__file__).resolve().parents[2] / ".cache" / "local"
)
USER = Path("/home/user")  # HOME inside the sandbox, as in the cloud image
CLAUDE_IN = Path("/tmp/cc/claude")
CREDENTIALS = Path.home() / ".claude" / ".credentials.json"
TOOLS = ("semble", "graphify")
# tools a one-shot headless session cannot use sensibly (web is forbidden by the prompt)
DISALLOWED = ("WebFetch,WebSearch,CronCreate,CronDelete,CronList,ScheduleWakeup,RemoteTrigger,"
              "PushNotification,Workflow,DesignSync,Monitor")  # fmt: skip
TOOL_CMD = {"semble": re.compile(r"\bsemble\b"), "graphify": re.compile(r"\bgraphify\b")}
# commands that reach the network (the semble instructions' "|| uvx" fallback does not count)
NETWORK_CMD = re.compile(r"\b(curl|wget|pip3? install|git\s+(fetch|pull|clone|ls-remote))\b")
# Claude Code 2.1.x words it "You've hit your 5-hour limit" (or weekly, Sonnet, ...)
LIMIT_TEXT = re.compile(r"usage limit|rate.?limit|limit reached|out of extra usage|hit your ",
                        re.I)  # fmt: skip
SESSION_TIMEOUT_S = 900
BUILD_TIMEOUT_S = 1800


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def access_token(min_left_s: int = 1200) -> str:
    """The account's current access token, read fresh (the main session refreshes it)."""
    oauth = json.loads(CREDENTIALS.read_text())["claudeAiOauth"]
    left = oauth["expiresAt"] / 1000 - time.time()
    if left < min_left_s:
        raise RuntimeError(f"access token expires in {left / 60:.0f} min: use Claude Code once")
    return oauth["accessToken"]


def sandbox(cwd: Path, mounts: list[tuple[str, Path, Path]]) -> list[str]:
    """bwrap argv: read-only system, empty /home /tmp /var/tmp /run/user, then ``mounts``.

    ``mounts`` are (``bind`` or ``ro-bind``, host path, sandbox path), applied in order.
    """
    hidden = ["/tmp", "/run/user", "/home", "/var/tmp"]
    for extra in (Path.home(), WORK):
        if not any(extra.is_relative_to(h) for h in hidden):
            hidden.append(str(extra))
    argv = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc"]
    for path in hidden:
        argv += ["--tmpfs", path]
    for kind, src, dst in mounts:
        argv += [f"--{kind}", str(src), str(dst)]
    return argv + ["--unshare-pid", "--unshare-ipc", "--die-with-parent", "--new-session",
                   "--chdir", str(cwd)]  # fmt: skip


def sandbox_env(**extra: str) -> dict[str, str]:
    return {
        "HOME": str(USER),
        "USER": "user",
        "LOGNAME": "user",
        "PATH": f"{USER}/.local/bin:/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "TERM": "dumb",
        "SHELL": "/bin/bash",
        "HF_HUB_OFFLINE": "1",
        "DISABLE_AUTOUPDATER": "1",
    } | extra


def setup_tools(root: Path) -> None:
    """Pinned tools in a template ``~/.local``, built in the sandbox so every path is neutral."""
    local, home, cache = WORK / "user-local", WORK / "setup-home", WORK / "uv-cache"
    for d in (local / "bin", home, cache):
        d.mkdir(parents=True, exist_ok=True)
    uv = Path(shutil.which("uv") or Path(sys.executable).parent / "uv").resolve()
    mounts = [("bind", home, USER), ("bind", local, USER / ".local"),
              ("bind", cache, USER / ".cache" / "uv"), ("ro-bind", uv, Path("/tmp/uv/uv")),
              ("ro-bind", root / "configs" / "envs", Path("/tmp/locks"))]  # fmt: skip
    env = sandbox_env(UV_PYTHON_INSTALL_DIR=f"{USER}/.local/share/uv/python",
                      UV_CACHE_DIR=f"{USER}/.cache/uv")  # fmt: skip
    for tool in TOOLS:
        venv = USER / ".local" / "share" / "uv" / "tools" / tool
        if not (local / "share" / "uv" / "tools" / tool / "bin" / tool).exists():
            log(f"installing {tool} from configs/envs/{tool}.txt")
            for cmd in (["venv", "-q", "--python", "3.13", "--python-preference", "only-managed",
                         str(venv)],
                        ["pip", "sync", "-q", "--python", str(venv / "bin" / "python"),
                         f"/tmp/locks/{tool}.txt"]):  # fmt: skip
                subprocess.run(sandbox(USER, mounts) + ["/tmp/uv/uv", *cmd], env=env, check=True)
        link = local / "bin" / tool
        if not link.is_symlink():
            link.symlink_to(Path("..") / "share" / "uv" / "tools" / tool / "bin" / tool)
    hf = WORK / "hf"
    if not (hf / "hub").exists():  # semble downloads its embedding model on first use
        hf.mkdir(parents=True, exist_ok=True)
        warm = WORK / "warmup"
        warm.mkdir(exist_ok=True)
        (warm / "a.py").write_text("def add(a, b):\n    return a + b\n")
        m = [("bind", home, USER), ("ro-bind", local, USER / ".local"),
             ("bind", hf, USER / ".cache" / "huggingface"),
             ("bind", warm, USER / "warm")]  # fmt: skip
        env = sandbox_env()
        env.pop("HF_HUB_OFFLINE")
        cmd = ["semble", "search", "add", str(USER / "warm")]
        subprocess.run(sandbox(USER, m) + cmd, env=env, check=True, capture_output=True)
        shutil.rmtree(warm)
        shutil.rmtree(home / ".cache" / "semble", ignore_errors=True)


def checkout(task: Task, tdir: Path, arms: list[str]) -> dict[str, Path]:
    """Depth-1 fetch of the base commit, then one identical copy per arm."""
    src = tdir / "src"
    if not (src / ".git").exists():
        subprocess.run(["git", "-c", "init.defaultBranch=main", "init", "-q", str(src)], check=True)
        fetch = ["git", "-C", str(src), "fetch", "-q", "--depth", "1"]
        for attempt in range(3):
            r = subprocess.run(fetch + [task.repo_url, task.base_commit], capture_output=True,
                               text=True)  # fmt: skip
            if r.returncode == 0:
                break
            log(f"fetch {task.repo} failed ({attempt + 1}/3): {r.stderr.strip()[-200:]}")
            time.sleep(10)
        else:
            raise RuntimeError(f"cannot fetch {task.repo}@{task.base_commit}")
        subprocess.run(["git", "-C", str(src), "-c", "advice.detachedHead=false", "checkout",
                        "-q", "--detach", "FETCH_HEAD"], check=True)  # fmt: skip
        (src / ".git" / "FETCH_HEAD").unlink(missing_ok=True)
    out = {}
    for arm in arms:
        dest = tdir / arm / "repo"
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["cp", "-a", str(src), str(dest)], check=True)
        out[arm] = dest
    return out


def arm_mounts(task: Task, tdir: Path, arm: str) -> list[tuple[str, Path, Path]]:
    """The arm's own HOME and checkout at neutral paths, shared tools and model read-only."""
    home = tdir / arm / "home"
    home.mkdir(parents=True, exist_ok=True)
    name = task.repo.split("/")[-1]
    return [("bind", home, USER), ("ro-bind", WORK / "user-local", USER / ".local"),
            ("ro-bind", WORK / "hf", USER / ".cache" / "huggingface"),
            ("bind", tdir / arm / "repo", USER / name)]  # fmt: skip


def prebuild(task: Task, tdir: Path, arm: str) -> dict:
    """Build the arm's index in its sandbox, at the path the session will use."""
    if arm not in TOOL_CMD:
        return {}
    repo_in = USER / task.repo.split("/")[-1]
    env = sandbox_env()
    if arm == "semble":
        cmd = ["semble", "search", "index warm-up", str(repo_in), "-k", "1",
               "--max-snippet-lines", "0"]  # fmt: skip
    else:
        cmd = ["graphify", "extract", ".", "--code-only"]
        env["GRAPHIFY_BACKEND"] = "none"
    t0 = time.monotonic()
    r = subprocess.run(sandbox(repo_in, arm_mounts(task, tdir, arm)) + cmd, env=env,
                       capture_output=True, text=True, timeout=BUILD_TIMEOUT_S)  # fmt: skip
    info = {"prebuild_s": round(time.monotonic() - t0, 2), "prebuild_ok": r.returncode == 0}
    if r.returncode:
        log(f"prebuild {arm} failed: {r.stderr.strip()[-300:]}")
    repo = tdir / arm / "repo"
    if arm == "semble":
        for stats in (tdir / arm / "home" / ".cache").rglob("savings.jsonl"):
            stats.unlink()  # the warm-up search is not the agent's use
    else:
        info["graph_built"] = (repo / "graphify-out" / "graph.json").exists()
        # keeps graphify-out/ out of git status, as the cloud protocol's setup line did
        with (repo / ".git" / "info" / "exclude").open("a") as f:
            f.write("graphify-out/\n")
    return info


def parse_stream(lines: list[str], arm: str) -> dict:
    """A Track B record from a ``claude -p --output-format stream-json`` transcript."""
    init: dict = {}
    result: dict | None = None
    bash: list[str] = []
    tools: list[str] = []
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            init = event
        elif kind == "assistant":
            for block in event.get("message", {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tools.append(block.get("name", ""))
                    if block.get("name") == "Bash":
                        bash.append(str((block.get("input") or {}).get("command", "")))
        elif kind == "result":
            result = event
    res = result or {}
    usage = res.get("usage") or {}
    server = usage.get("server_tool_use") or {}
    ok = bool(result) and res.get("subtype") == "success" and not res.get("is_error")
    text = res.get("result") or ""
    limit = LIMIT_TEXT.search(text) or res.get("api_error_status") == 429
    status = "ok" if ok else ("limit" if limit else "error")
    return {
        "session_id": res.get("session_id") or init.get("session_id"),
        "model": init.get("model"),
        "status": status,
        "result_text": text,
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cache_read_tokens": usage.get("cache_read_input_tokens"),
        "cache_creation_tokens": usage.get("cache_creation_input_tokens"),
        "num_turns": res.get("num_turns"),
        "duration_s": res["duration_ms"] / 1000 if "duration_ms" in res else None,
        "cost_usd": res.get("total_cost_usd"),
        "web_requests": (server.get("web_search_requests") or 0)
        + (server.get("web_fetch_requests") or 0),
        "permission_denials": len(res.get("permission_denials") or []),
        "tool_calls": sum(bool(TOOL_CMD[arm].search(c)) for c in bash) if arm in TOOL_CMD else None,
        "network_commands": sum(bool(NETWORK_CMD.search(c)) for c in bash),
        "subagent_calls": sum(name in ("Task", "Agent") for name in tools),
        "claude_code_version": init.get("claude_code_version"),
        "harness": "local-cli",
    }


def run_session(cfg: dict, root: Path, task: Task, arm: str, tdir: Path) -> dict:
    req = session_request(cfg, root, task, arm)
    claude = Path(shutil.which("claude") or "claude").resolve()
    mounts = arm_mounts(task, tdir, arm) + [("ro-bind", claude, CLAUDE_IN)]
    env = sandbox_env(CLAUDE_CODE_OAUTH_TOKEN=access_token())
    cmd = [str(CLAUDE_IN), "-p", req["prompt"], "--model", req["model"],
           "--output-format", "stream-json", "--verbose", "--no-session-persistence",
           "--permission-mode", "bypassPermissions", "--strict-mcp-config",
           "--mcp-config", '{"mcpServers":{}}', "--disallowedTools", DISALLOWED]  # fmt: skip
    t0 = time.monotonic()
    try:
        r = subprocess.run(sandbox(USER / task.repo.split("/")[-1], mounts) + cmd, env=env,
                           text=True, capture_output=True, stdin=subprocess.DEVNULL,
                           timeout=SESSION_TIMEOUT_S)  # fmt: skip
        out, err = r.stdout, r.stderr
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else exc.stdout or ""
        err = "timeout"
    wall = round(time.monotonic() - t0, 2)
    logs = WORK / "logs" / cfg["run"] / arm
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{task.instance_id}.jsonl.gz").write_bytes(gzip.compress(out.encode()))
    rec = parse_stream(out.splitlines(), arm)
    rec |= {"task_id": task.instance_id, "arm": arm, "wall_s": wall}
    if rec["status"] != "ok":
        rec["error"] = (err or "")[-500:]
    return rec


def record_path(root: Path, run: str, arm: str, task_id: str) -> Path:
    return root / ".cache" / "trackb" / run / arm / f"{task_id}.json"


def run(cfg: dict, root: Path, tasks: list[Task], parallel: int = 2,
        budget_s: float | None = None) -> bool:  # fmt: skip
    """Run every missing (task, arm) session; True when all are done."""
    setup_tools(root)
    arms = list(cfg["arms"])
    stop = threading.Event()
    start = time.monotonic()

    def pending(task: Task) -> list[str]:
        out = []
        for arm in arms:
            p = record_path(root, cfg["run"], arm, task.instance_id)
            if not (p.exists() and json.loads(p.read_text()).get("status") == "ok"):
                out.append(arm)
        return out

    def one(task: Task) -> None:
        todo = pending(task)
        if not todo or stop.is_set() or (budget_s and time.monotonic() - start > budget_s):
            return
        tdir = WORK / "tasks" / task.instance_id
        try:
            checkout(task, tdir, todo)
            builds = {arm: prebuild(task, tdir, arm) for arm in todo}
            with ThreadPoolExecutor(len(todo)) as pool:
                futures = {a: pool.submit(run_session, cfg, root, task, a, tdir) for a in todo}
                recs = {a: f.result() for a, f in futures.items()}
            for arm, rec in recs.items():
                rec |= builds[arm]
                p = record_path(root, cfg["run"], arm, task.instance_id)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps(rec, indent=1, sort_keys=True))
                if rec["status"] == "limit":
                    stop.set()
                log(f"{task.instance_id[-8:]} {arm:9s} {rec['status']:5s} "
                    f"{rec.get('duration_s') or 0:5.0f} s ${rec.get('cost_usd') or 0:.4f} "
                    f"turns {rec.get('num_turns')} tool {rec.get('tool_calls')}")  # fmt: skip
        except Exception as exc:  # one broken task must not stop the run
            log(f"{task.instance_id[-8:]} failed: {exc}")
        finally:
            shutil.rmtree(tdir, ignore_errors=True)

    with ThreadPoolExecutor(parallel) as pool:
        list(pool.map(one, tasks))
    return not any(pending(t) for t in tasks)
