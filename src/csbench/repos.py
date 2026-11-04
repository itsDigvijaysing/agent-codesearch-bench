"""Checkouts of target repositories at a task's base commit.

One blobless bare clone per repository (``git clone --bare --filter=blob:none``) is shared by
all tasks; each task gets a detached ``git worktree`` that is removed after the task. Local
repositories (``csbench try``) are cloned without a filter.
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
        if Path(url).is_dir():
            # A local repository: plain local clone (hardlinked objects). A blob filter here
            # would make the user's repository a lazy-fetch source, which can fork-storm when
            # that repository is itself shallow or partial.
            _git("clone", "--quiet", "--bare", "--no-hardlinks", url, str(bare))
        else:
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


def count_files(cache: Path, repo: str, url: str, commit: str) -> int:
    """Tracked files at ``commit``, from a shallow tree-only fetch of that one commit."""
    git_dir = cache / "sizes" / (repo.replace("/", "__") + ".git")
    if not git_dir.exists():
        _git("init", "--quiet", "--bare", str(git_dir))
    try:
        _git("--git-dir", str(git_dir), "cat-file", "-e", f"{commit}^{{commit}}")
    except subprocess.CalledProcessError:
        _git("--git-dir", str(git_dir), "fetch", "--quiet", "--depth", "1",
             "--filter=blob:none", url, commit)  # fmt: skip
    out = _git("--git-dir", str(git_dir), "ls-tree", "-r", "--name-only", commit).stdout
    return len(out.splitlines())
