"""Shared corpus definition for the baselines: git-tracked regular text files up to 1 MB."""

from __future__ import annotations

import subprocess
from pathlib import Path

MAX_FILE_BYTES = 1_000_000


def is_text(path: Path) -> bool:
    with path.open("rb") as fh:
        return b"\0" not in fh.read(8192)


def list_files(repo: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z"], check=True, capture_output=True
    ).stdout.decode()
    files = []
    for rel in sorted(filter(None, out.split("\0"))):
        p = repo / rel
        if p.is_file() and not p.is_symlink() and p.stat().st_size <= MAX_FILE_BYTES and is_text(p):
            files.append(rel)
    return files


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
