"""``csbench try <repo>``: benchmark the tools on your own repository's history.

There is no human-annotated gold context for an arbitrary project, so tasks are mined from
its git history, the same way commit-based code benchmarks are built:

- candidates are recent non-merge commits whose message has at least 30 characters and does
  not look like housekeeping (version bumps, releases, merges, reverts, formatting, typos);
- the commit must modify between 1 and ``max_files`` existing non-test files (and at most 10
  files in total), so it is a focused change;
- the query is the commit message (subject and body, without trailers), standing in for an
  issue description;
- the gold context is the lines the commit changed, in the version before the commit (for a
  pure insertion, the line it was inserted after).

Every tool then runs on the parent commit, exactly as in the main benchmark, and the usual
report is written to the output directory. Commit messages are written after the fix and
often name the changed code, so absolute scores are optimistic; the ranking of tools on the
same tasks is the useful part.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from csbench.config import Config, cache_root
from csbench.dataset import Task
from csbench.intervals import Interval, merge

_SKIP = re.compile(
    r"^\s*(bump|release|merge|revert|version|v?\d+\.\d+|format|reformat|lint|typo|"
    r"update (deps|dependencies|changelog)|chore|ci|docs?)\b",
    re.IGNORECASE,
)
_TEST = re.compile(r"(^|/)(tests?|testing|__tests__|spec)/|(^|/)test_[^/]*$|"
                   r"_test\.\w+$|\.(test|spec)\.\w+$")  # fmt: skip
_TRAILER = re.compile(r"^[A-Za-z-]+: .+$")
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def message(raw: str) -> str:
    """Commit message without trailing trailers such as Signed-off-by."""
    lines = raw.strip().splitlines()
    while lines and (_TRAILER.match(lines[-1]) or not lines[-1].strip()):
        lines.pop()
    return "\n".join(lines).strip()


def gold_from_diff(diff: str) -> tuple[dict[str, list[Interval]], int]:
    """Changed lines per pre-image file, and the number of files the diff touches."""
    gold: dict[str, list[Interval]] = {}
    files = 0
    current: str | None = None
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            files += 1
            current = None
        elif line.startswith("--- "):
            path = line[4:].strip()
            current = None if path == "/dev/null" else path.removeprefix("a/")
        elif current and (m := _HUNK.match(line)):
            start, count = int(m.group(1)), int(m.group(2) or 1)
            span = (max(start, 1), max(start, 1)) if count == 0 else (start, start + count - 1)
            gold.setdefault(current, []).append(span)
    gold = {f: merge(iv) for f, iv in gold.items() if not _TEST.search(f)}
    return gold, files


def mine_tasks(repo: Path, n: int, max_files: int = 5, scan: int = 3000) -> list[Task]:
    repo = repo.resolve()
    name = repo.name
    log = _git(repo, "log", "--no-merges", f"-n{scan}", "--format=%H%x00%P%x00%B%x1e")
    tasks = []
    for entry in log.split("\x1e"):
        parts = entry.strip("\n").split("\x00")
        if len(parts) != 3:
            continue
        sha, parents, body = parts
        msg = message(body)
        if len(parents.split()) != 1 or len(msg) < 30 or _SKIP.match(msg):
            continue
        diff = _git(repo, "diff", "-U0", "--no-color", "--no-renames", parents, sha)
        gold, touched = gold_from_diff(diff)
        if not 1 <= len(gold) <= max_files or touched > 10:
            continue
        tasks.append(
            Task(
                f"{name}-{sha[:12]}", f"local/{name}", str(repo), "any", parents, msg, "local", gold
            )  # fmt: skip
        )
        if len(tasks) == n:
            break
    return tasks


def config(root: Path, repo: Path, out_dir: Path, tools: list[str] | None) -> Config:
    """A run configuration for the user's repository, reusing the pinned tool definitions."""
    base = Config.load(root / "configs" / "v1.yaml").raw
    head = _git(repo, "rev-parse", "HEAD").strip()
    raw = {
        **base,
        "run": "try",
        "dataset": {
            "repo_id": f"git history of {repo.name}",
            "config": "csbench try",
            "revision": head,
            "file": "",
        },
        "sample": {"file": str(out_dir / "tasks.txt")},
        "tools": tools or base["tools"],
        "paths": {"cache": str(cache_root(root)), "raw": str(out_dir), "results": str(out_dir)},
    }
    return Config(raw, root)


def run(root: Path, repo: Path, out_dir: Path, n: int, tools: list[str] | None,
        time_budget_s: float | None) -> tuple[Path, bool]:  # fmt: skip
    from csbench import report, runner

    repo, out_dir = repo.resolve(), out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = mine_tasks(repo, n)
    if not tasks:
        raise SystemExit(f"no suitable commits found in {repo}")
    (out_dir / "tasks.txt").write_text("".join(t.instance_id + "\n" for t in tasks))
    cfg = config(root, repo, out_dir, tools)
    runner.log(f"{len(tasks)} tasks mined from {repo}; results in {out_dir}")
    _, complete = runner.run(cfg, tasks=tasks, time_budget_s=time_budget_s)
    if complete:
        report.write(cfg, cfg["tools"], readme=False)
    return out_dir / cfg.run_name, complete
