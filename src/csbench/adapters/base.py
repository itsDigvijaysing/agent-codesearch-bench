"""Adapter interface. Each adapter runs inside a fresh worker process (see ``worker.py``)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Hit:
    """One ranked result. ``start``/``end`` are 1-based inclusive lines; None means whole file."""

    file: str
    start: int | None = None
    end: int | None = None
    score: float = 0.0


class Adapter:
    name = ""
    has_spans = True

    def __init__(self, **params):
        self.params = params

    def version(self) -> str:
        raise NotImplementedError

    def build(self, repo: Path, index_dir: Path) -> None:
        """Build any index. ``index_dir`` is measured for index size afterwards."""

    def search(self, query: str, top_k: int) -> list[Hit]:
        raise NotImplementedError
