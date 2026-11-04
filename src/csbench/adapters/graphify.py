"""graphify (https://github.com/Graphify-Labs/graphify), deterministic AST code mode only.

Build: ``graphify extract <repo> --code-only`` with ``GRAPHIFY_BACKEND=none``, the documented
way to keep a code-only graph with every LLM backend disabled (tree-sitter AST, no network).
Query: ``graphify query "<issue text>" --graph <graph.json>`` with default settings (BFS,
depth 2, 2,000-token budget). graphify answers with graph nodes, each giving a file and a
start line (``NODE <label> [src=<file> loc=L<n> ...]``), not code. Results are therefore scored
as locations: files are ranked by first appearance, span and token-budget metrics are not
applicable, and tokens returned is the size of graphify's own output. graphify sizes its
answer by token budget, not by a result count, so ``top_k`` is not applied.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from csbench.adapters.base import Adapter, Hit

_NODE = re.compile(r"^NODE .*?\[src=(.+?) loc=L(\d+)", re.MULTILINE)
_ENV = {"GRAPHIFY_BACKEND": "none", "GRAPHIFY_QUERY_LOG_DISABLE": "1"}


def parse_nodes(text: str) -> list[Hit]:
    return [Hit(src, int(line), int(line)) for src, line in _NODE.findall(text)]


class GraphifyAdapter(Adapter):
    name = "graphify"
    has_spans = False
    returns_code = False

    def version(self) -> str:
        return f"graphifyy {version('graphifyy')}"

    def _run(self, *args: str, cwd: Path) -> subprocess.CompletedProcess:
        exe = str(Path(sys.executable).parent / "graphify")
        return subprocess.run(
            [exe, *args], cwd=cwd, env={**os.environ, **_ENV}, capture_output=True, text=True
        )

    def build(self, repo: Path, index_dir: Path) -> None:
        self.repo = repo
        proc = self._run("extract", str(repo), "--code-only", cwd=repo)
        out = repo / "graphify-out"
        if proc.returncode != 0 or not (out / "graph.json").exists():
            raise RuntimeError(f"graphify extract failed: {proc.stderr.strip()[-500:]}")
        shutil.move(str(out), index_dir / "graphify-out")
        self.graph = index_dir / "graphify-out" / "graph.json"

    def search(self, query: str, top_k: int) -> list[Hit]:
        proc = self._run("query", query, "--graph", str(self.graph), cwd=self.repo)
        if proc.returncode not in (0, 3, 4):  # 3: ambiguous name, 4: no matching node
            raise RuntimeError(f"graphify query failed: {proc.stderr.strip()[-500:]}")
        self.raw_output = proc.stdout
        return parse_nodes(proc.stdout)
