"""semble (https://github.com/MinishLab/semble) through its documented Python API.

``SembleIndex.from_path(repo)`` with default settings (code content only), then
``index.search(query, top_k)``. The default embedding model is pinned to a Hugging Face
revision and passed with the documented ``model_path`` argument; it is downloaded once in
``prepare()``, outside the timed build. The built index is written with the public
``SembleIndex.save`` (as the CLI caches it on first run), so build time includes saving and the
index size is measured. ``SEMBLE_CACHE_LOCATION`` points at the per-task index directory, so no
cached index is ever reused across tasks.
"""

from __future__ import annotations

import os
from importlib.metadata import version
from pathlib import Path

from csbench.adapters.base import Adapter, Hit


class SembleAdapter(Adapter):
    name = "semble"
    has_spans = True

    def version(self) -> str:
        return f"semble {version('semble')}"

    def _model_path(self) -> str:
        from huggingface_hub import snapshot_download

        return snapshot_download(self.params["model"], revision=self.params["model_revision"])

    def prepare(self) -> None:
        self._model_path()

    def build(self, repo: Path, index_dir: Path) -> None:
        os.environ["SEMBLE_CACHE_LOCATION"] = str(index_dir.resolve())
        from semble import SembleIndex

        self.index = SembleIndex.from_path(repo, model_path=self._model_path())
        self.index.save(index_dir / "index")

    def search(self, query: str, top_k: int) -> list[Hit]:
        return [
            Hit(r.chunk.file_path, r.chunk.start_line, r.chunk.end_line, float(r.score))
            for r in self.index.search(query, top_k=top_k)
        ]
