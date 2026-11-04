"""ContextBench loader.

Dataset: ContextBench (Apache-2.0), https://github.com/EuniAI/ContextBench, arXiv 2602.05892.
Hugging Face dataset ``Contextbench/ContextBench``, config ``contextbench_verified``.
``gold_context`` is a JSON list of ``{file, start_line, end_line, content}`` spans with
1-based inclusive line numbers (see the dataset card).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pyarrow.parquet as pq

from csbench.intervals import Interval, merge


@dataclass(frozen=True)
class Task:
    instance_id: str
    repo: str
    repo_url: str
    language: str
    base_commit: str
    problem_statement: str
    source: str
    gold_lines: dict[str, list[Interval]] = field(hash=False)

    @property
    def gold_files(self) -> set[str]:
        return set(self.gold_lines)


def normalize_path(path: str) -> str:
    """Repository-relative POSIX path, as ContextBench's ``_normalize_rel_path`` does."""
    p = path.replace("\\", "/").strip()
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def parse_gold(gold_json: str) -> dict[str, list[Interval]]:
    """Gold context to merged line intervals per file."""
    by_file: dict[str, list[Interval]] = {}
    for span in json.loads(gold_json):
        start = int(span.get("start_line") or 1)
        end = int(span.get("end_line") or start)
        by_file.setdefault(normalize_path(span["file"]), []).append((start, max(start, end)))
    return {f: merge(iv) for f, iv in by_file.items()}


def download(repo_id: str, revision: str, filename: str, raw_dir: Path) -> Path:
    """Fetch the parquet file at a pinned dataset revision into ``raw_dir``."""
    from huggingface_hub import hf_hub_download

    return Path(
        hf_hub_download(
            repo_id=repo_id,
            repo_type="dataset",
            revision=revision,
            filename=filename,
            local_dir=raw_dir,
        )
    )


def load_tasks(parquet_path: Path) -> list[Task]:
    rows = pq.read_table(parquet_path).to_pylist()
    return [
        Task(
            instance_id=r["instance_id"],
            repo=r["repo"],
            repo_url=r["repo_url"],
            language=r["language"],
            base_commit=r["base_commit"],
            problem_statement=r["problem_statement"] or "",
            source=r["source"],
            gold_lines=parse_gold(r["gold_context"]),
        )
        for r in rows
    ]
