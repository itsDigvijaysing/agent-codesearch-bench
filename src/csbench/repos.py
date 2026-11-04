"""Checkouts of target repositories at a task's base commit.

One blobless bare clone per repository (``git clone --bare --filter=blob:none``) is shared by
all tasks; each task gets a detached ``git worktree`` that is removed after the task.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True)


def bare_path(cache: Path, repo: str) -> Path:
    return cache / "repos" / (repo.replace("/", "__") + ".git")


def checkout(cache: Path, repo: str, url: str, commit: str, dest: Path) -> Path:
    bare = bare_path(cache, repo)
    if not bare.exists():
        bare.parent.mkdir(parents=True, exist_ok=True)
        _git("clone", "--quiet", "--bare", "--filter=blob:none", url, str(bare))
    try:
        _git("--git-dir", str(bare), "cat-file", "-e", f"{commit}^{{commit}}")
    except subprocess.CalledProcessError:
        _git("--git-dir", str(bare), "fetch", "--quiet", "origin", commit)
    remove(cache, repo, dest)
    _git("--git-dir", str(bare), "worktree", "add", "--quiet", "--detach", str(dest), commit)
    return dest


def remove(cache: Path, repo: str, dest: Path) -> None:
    bare = bare_path(cache, repo)
    if dest.exists():
        shutil.rmtree(dest)
    if bare.exists():
        _git("--git-dir", str(bare), "worktree", "prune")


def dir_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(p.lstat().st_size for p in path.rglob("*") if p.is_file() and not p.is_symlink())
