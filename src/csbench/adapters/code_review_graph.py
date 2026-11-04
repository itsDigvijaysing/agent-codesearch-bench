"""code-review-graph (https://github.com/tirth8205/code-review-graph) through its CLI.

Build: ``code-review-graph build --repo <repo>`` with default post-processing; the graph
database goes to the per-task index directory through the documented ``CRG_DATA_DIR``
variable. Query: ``code-review-graph search "<issue text>" --limit K --repo <repo>``. With the
default install no embedding provider is configured, so search is keyword full-text search
(FTS5) and needs no LLM or network. Each result is a code entity with a file and a line
range, and its signature rather than its code, so results are scored as locations with spans:
span metrics use the entity ranges, token-budget metrics are not applicable, and tokens
returned is the size of the tool's own JSON output.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from csbench.adapters.base import Adapter, Hit


def parse_results(stdout: str, repo: Path) -> list[Hit]:
    data = json.loads(stdout[stdout.index("{") :])
    hits = []
    for r in data.get("results", []):
        path = r["file_path"]
        rel = os.path.relpath(path, repo) if os.path.isabs(path) else path
        start = r.get("line_start")
        hits.append(Hit(rel, start, r.get("line_end") or start, float(r.get("score") or 0)))
    return hits


class CodeReviewGraphAdapter(Adapter):
    name = "code-review-graph"
    has_spans = True
    returns_code = False

    def version(self) -> str:
        return f"code-review-graph {version('code-review-graph')}"

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        exe = str(Path(sys.executable).parent / "code-review-graph")
        env = {**os.environ, "CRG_DATA_DIR": str(self.index_dir)}
        return subprocess.run([exe, *args], env=env, capture_output=True, text=True)

    def build(self, repo: Path, index_dir: Path) -> None:
        self.repo, self.index_dir = repo.resolve(), index_dir.resolve()
        proc = self._run("build", "--repo", str(self.repo), "--quiet")
        if proc.returncode != 0:
            raise RuntimeError(f"code-review-graph build failed: {proc.stderr.strip()[-500:]}")

    def search(self, query: str, top_k: int) -> list[Hit]:
        proc = self._run("search", query, "--limit", str(top_k), "--repo", str(self.repo))
        if proc.returncode != 0:
            raise RuntimeError(f"code-review-graph search failed: {proc.stderr.strip()[-500:]}")
        self.raw_output = proc.stdout
        return parse_results(proc.stdout, self.repo)
