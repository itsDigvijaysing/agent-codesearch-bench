"""Resumable runner: one result file per (tool, task); completed pairs are skipped."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from functools import cache
from pathlib import Path

from csbench import repos
from csbench.adapters import get_adapter
from csbench.config import Config, ToolSpec
from csbench.dataset import Task, download, load_tasks, normalize_path
from csbench.files import read_lines
from csbench.metrics import ResolvedHit, ranked_files, task_metrics, zero_metrics
from csbench.sample import first_candidates, select, select_hard

STORED_HITS = 50  # hits kept per record; metrics are computed on all hits


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


@cache
def _encoder(name: str):
    import tiktoken

    return tiktoken.get_encoding(name)


def dataset_path(cfg: Config) -> Path:
    d = cfg["dataset"]
    local = cfg.path("raw") / d["file"]
    if local.exists():
        return local
    return download(d["repo_id"], d["revision"], d["file"], cfg.path("raw"))


def sample_ids(cfg: Config) -> list[str]:
    path = cfg.root / cfg["sample"]["file"]
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def write_sample(cfg: Config) -> Path:
    s = cfg["sample"]
    tasks = load_tasks(dataset_path(cfg))
    if s.get("kind") == "hard":
        exclude = set((cfg.root / s["exclude"]).read_text().split())
        firsts = first_candidates(tasks, exclude, s["min_gold_files"])
        sizes = {
            repo: repos.count_files(cfg.path("cache"), repo, t.repo_url, t.base_commit)
            for repo, t in firsts.items()
        }
        for repo, n in sorted(sizes.items(), key=lambda x: -x[1]):
            log(f"{repo}: {n} tracked files")
        ids = select_hard(
            tasks,
            exclude=exclude,
            repo_files=sizes,
            min_gold_files=s["min_gold_files"],
            min_repo_files=s["min_repo_files"],
            per_repo=s["per_repo"],
            seed=s["seed"],
        )
    else:
        ids = select(
            tasks,
            language=s["language"],
            max_repos=s["max_repos"],
            n_tasks=s["n_tasks"],
            seed=s["seed"],
        )
    path = cfg.root / s["file"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(ids) + "\n")
    return path


def selected_tasks(cfg: Config, limit: int | None = None) -> list[Task]:
    by_id = {t.instance_id: t for t in load_tasks(dataset_path(cfg))}
    return [by_id[i] for i in sample_ids(cfg)[:limit]]


def pair_path(cfg: Config, tool: str, task_id: str) -> Path:
    return cfg.path("cache") / "runs" / cfg.run_name / tool / f"{task_id}.json"


def committed_records(cfg: Config, tool: str) -> dict[str, dict]:
    """Records already in ``results/``; they let a run resume across sessions."""
    path = cfg.path("results") / cfg.run_name / "per_task" / f"{tool}.jsonl.gz"
    if not path.exists():
        return {}
    with gzip.open(path, "rt") as fh:
        return {r["task_id"]: r for r in map(json.loads, fh)}


def load_record(cfg: Config, spec: ToolSpec, task_id: str, committed: dict) -> dict | None:
    fp = cfg.fingerprint(spec)
    p = pair_path(cfg, spec.name, task_id)
    rec = json.loads(p.read_text()) if p.exists() else committed.get(task_id)
    return rec if rec and rec.get("fingerprint") == fp else None


def resolve_hits(repo: Path, hits: list[dict], encoder_name: str) -> list[ResolvedHit]:
    enc = _encoder(encoder_name)
    files: dict[str, list[str] | None] = {}
    out = []
    for h in hits:
        rel = h["file"]
        if os.path.isabs(rel):
            rel = os.path.relpath(rel, repo)
        rel = normalize_path(rel)
        if rel not in files:
            p = repo / rel
            files[rel] = read_lines(p) if p.is_file() else None
        lines = files[rel]
        if not lines:
            out.append(ResolvedHit(rel, 1, 0, ()))
            continue
        start = max(1, h.get("start") or 1)
        end = min(len(lines), h.get("end") or len(lines))
        counts = tuple(len(t) for t in enc.encode_ordinary_batch(lines[start - 1 : end]))
        out.append(ResolvedHit(rel, start, end, counts))
    return out


def tool_python(cfg: Config, spec: ToolSpec) -> str:
    """Interpreter for a tool: its own venv, installed exactly from its committed lock file.

    Each tool gets the dependency versions its own users would get, independent of the
    benchmark's environment and of the other tools. Baselines without ``env`` use this one.
    """
    if not spec.env:
        return sys.executable
    lock = cfg.root / spec.env
    env_dir = cfg.path("cache") / "envs" / spec.name
    marker = env_dir / ".csbench-lock-sha256"
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    python = env_dir / "bin" / "python"
    if not (marker.exists() and marker.read_text() == digest and python.exists()):
        log(f"{spec.name}: creating environment from {spec.env}")
        shutil.rmtree(env_dir, ignore_errors=True)
        py = f"{sys.version_info.major}.{sys.version_info.minor}"
        subprocess.run(["uv", "venv", "-q", "--python", py, str(env_dir)], check=True)
        subprocess.run(["uv", "pip", "sync", "-q", "--python", str(python), str(lock)], check=True)
        marker.write_text(digest)
    return str(python)


def lock_env(cfg: Config, spec: ToolSpec) -> Path:
    """Resolve the tool's pin to a fully pinned, hashed, cross-platform lock file."""
    out = cfg.root / spec.env
    out.parent.mkdir(parents=True, exist_ok=True)
    py = f"{sys.version_info.major}.{sys.version_info.minor}"
    cmd = [
        "uv",
        "pip",
        "compile",
        "-q",
        "--universal",
        "--generate-hashes",
        "--python-version",
        py,
        "--no-header",
        "--output-file",
        str(out),
        "-",
    ]
    subprocess.run(cmd, input=spec.pin + "\n", text=True, check=True)
    return out


def run_worker(spec: dict, timeout: float, python: str = sys.executable) -> dict:
    """Run the worker in its own session; kill the whole group on timeout."""
    spec_path = Path(spec["out"]).with_suffix(".spec.json")
    spec_path.write_text(json.dumps(spec))
    src = str(Path(__file__).resolve().parent.parent)  # makes csbench importable in tool venvs
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(filter(None, [src, os.environ.get("PYTHONPATH")])),
    }
    proc = subprocess.Popen(
        [python, "-m", "csbench.worker", str(spec_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        start_new_session=True,
        env=env,
    )
    timer = threading.Timer(timeout, lambda: os.killpg(proc.pid, signal.SIGKILL))
    timer.start()
    stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
    proc.wait()
    timed_out = not timer.is_alive()
    timer.cancel()
    spec_path.unlink(missing_ok=True)
    out_path = Path(spec["out"])
    if out_path.exists():
        result = json.loads(out_path.read_text())
        out_path.unlink()
    else:
        reason = f"timeout after {timeout:.0f}s" if timed_out else f"exit {proc.returncode}"
        result = {"status": "error", "error": f"worker died: {reason}", "stderr": stderr[-2000:]}
    return result


def metric_kwargs(cfg: Config, spec: ToolSpec) -> dict:
    m = cfg["metrics"]
    adapter = get_adapter(spec.adapter)
    return {
        "ks": tuple(m["ks"]),
        "precision_ks": tuple(m["precision_ks"]),
        "budgets": tuple(m["budgets"]),
        "has_spans": adapter.has_spans,
        "returns_code": adapter.returns_code,
    }


def prepare(cfg: Config, spec: ToolSpec) -> None:
    """Run the adapter's one-time setup (e.g. pinned model download) outside any timing."""
    tmp = cfg.path("cache") / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    out = run_worker(
        {
            "adapter": spec.adapter,
            "params": spec.params,
            "prepare_only": True,
            "out": str(tmp / f"{spec.name}__prepare.json"),
        },
        float(cfg["timeout_s"]),
        tool_python(cfg, spec),
    )
    if out["status"] != "ok":
        log(f"{spec.name}: prepare failed: {out.get('error')}")


def evaluate_pair(cfg: Config, spec: ToolSpec, task: Task, repo_dir: Path) -> dict:
    index_dir = cfg.path("cache") / "index" / spec.name / task.instance_id
    shutil.rmtree(index_dir, ignore_errors=True)
    tmp = cfg.path("cache") / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    worker_spec = {
        "adapter": spec.adapter,
        "params": spec.params,
        "repo": str(repo_dir),
        "index_dir": str(index_dir),
        "query": task.problem_statement,
        "top_k": cfg["top_k"],
        "out": str(tmp / f"{spec.name}__{task.instance_id}.json"),
    }
    result = run_worker(worker_spec, float(cfg["timeout_s"]), tool_python(cfg, spec))
    index_bytes = repos.dir_bytes(index_dir)
    shutil.rmtree(index_dir, ignore_errors=True)

    kwargs = metric_kwargs(cfg, spec)
    rec = {
        "tool": spec.name,
        "task_id": task.instance_id,
        "repo": task.repo,
        "fingerprint": cfg.fingerprint(spec),
        "pin": spec.pin,
        "version": result.get("version"),
        "status": result["status"],
    }
    if result["status"] == "ok":
        hits = resolve_hits(repo_dir, result["hits"], cfg["metrics"]["tokenizer"])
        if not kwargs["returns_code"]:  # location tools: count what the agent actually receives
            raw = result.get("raw_output") or ""
            kwargs["output_tokens"] = len(
                _encoder(cfg["metrics"]["tokenizer"]).encode_ordinary(raw)
            )
        rec["metrics"] = task_metrics(task.gold_lines, hits, **kwargs)
        rec.update(
            build_s=round(result["build_s"], 4),
            query_s=round(result["query_s"], 4),
            index_bytes=index_bytes,
            peak_rss_mib=round(result["peak_rss_mib"], 1),
            files=ranked_files(hits)[:20],
            n_hits=len(hits),
            hits=[[h.file, h.start, h.end, h.tokens] for h in hits[:STORED_HITS]],
        )
    else:
        rec["metrics"] = zero_metrics(task_metrics(task.gold_lines, [], **kwargs))
        rec["error"] = result.get("error", "unknown error")
    return rec


def run(
    cfg: Config,
    *,
    tools: list[str] | None = None,
    limit: int | None = None,
    retry_failed: bool = False,
    time_budget_s: float | None = None,
    use_committed: bool = True,
    tasks: list[Task] | None = None,
) -> tuple[int, bool]:
    """Evaluate pending (tool, task) pairs; return (pairs evaluated, whether all are done)."""
    started = time.monotonic()
    specs = [s for s in cfg.tools(tools) if s.status == "active"]
    committed = {s.name: committed_records(cfg, s.name) if use_committed else {} for s in specs}
    cache_dir = cfg.path("cache")
    done = 0
    prepared: set[str] = set()
    for n, task in enumerate(tasks or selected_tasks(cfg, limit), 1):
        pending = []
        for s in specs:
            rec = load_record(cfg, s, task.instance_id, committed[s.name])
            if rec is None or (retry_failed and rec["status"] != "ok"):
                pending.append(s)
        if not pending:
            continue
        if time_budget_s is not None and time.monotonic() - started > time_budget_s:
            log("time budget reached; stopping (rerun to resume)")
            return done, False
        work = cache_dir / "work" / task.instance_id
        try:
            repos.checkout(cache_dir, task.repo, task.repo_url, task.base_commit, work)
        except subprocess.CalledProcessError as exc:
            msg = f"checkout failed: {(exc.stderr or '').strip()[:500]}"
            log(f"{task.instance_id}: {msg}")
            for s in pending:
                write_record(cfg, failed_checkout(cfg, s, task, msg))
            continue
        for s in pending:
            if s.name not in prepared:
                prepare(cfg, s)
                prepared.add(s.name)
            rec = evaluate_pair(cfg, s, task, work)
            write_record(cfg, rec)
            done += 1
            r10 = rec["metrics"]["file_recall@10"]
            log(f"[{n}] {s.name} {task.instance_id} {rec['status']} recall@10={r10:.2f}")
        repos.remove(cache_dir, task.repo, work)
        enforce_disk_limit(cfg)
    log(f"finished: {done} pair(s) evaluated")
    return done, True


def failed_checkout(cfg: Config, spec: ToolSpec, task: Task, msg: str) -> dict:
    template = task_metrics(task.gold_lines, [], **metric_kwargs(cfg, spec))
    return {
        "tool": spec.name,
        "task_id": task.instance_id,
        "repo": task.repo,
        "fingerprint": cfg.fingerprint(spec),
        "pin": spec.pin,
        "version": None,
        "status": "error",
        "error": msg,
        "metrics": zero_metrics(template),
    }


def write_record(cfg: Config, rec: dict) -> None:
    p = pair_path(cfg, rec["tool"], rec["task_id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec))


def enforce_disk_limit(cfg: Config) -> None:
    cache_dir = cfg.path("cache")
    limit = float(cfg["max_cache_gb"]) * 1e9
    if repos.dir_bytes(cache_dir) > limit:
        log("cache over limit: deleting cloned repositories and indexes")
        for sub in ("repos", "index", "work"):
            shutil.rmtree(cache_dir / sub, ignore_errors=True)
