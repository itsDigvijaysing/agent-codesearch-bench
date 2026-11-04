"""BM25 baseline: bm25s over fixed-size line chunks of the shared corpus (``files.py``).

Chunks are ``chunk_lines`` (default 50) consecutive lines, no overlap. Tokenizer: split on
non-alphanumeric characters (so snake_case splits), split camelCase/CamelCase boundaries,
lowercase, drop tokens shorter than 2 characters. No stopword list. BM25 parameters are
bm25s defaults (Lucene variant, k1=1.5, b=0.75). The query is the issue text, tokenized the
same way. Returns the top ``top_k`` chunks.
"""

from __future__ import annotations

import re
from importlib.metadata import version
from pathlib import Path

from csbench.adapters.base import Adapter, Hit
from csbench.files import list_files, read_lines

_WORD = re.compile(r"[A-Za-z0-9]+")
_CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def tokenize(text: str) -> list[str]:
    out = []
    for word in _WORD.findall(text):
        for part in _CAMEL.findall(word):
            if len(part) >= 2:
                out.append(part.lower())
    return out


def chunk(lines: list[str], size: int) -> list[tuple[int, int, str]]:
    return [
        (i + 1, min(i + size, len(lines)), "".join(lines[i : i + size]))
        for i in range(0, len(lines), size)
    ]


class BM25Adapter(Adapter):
    name = "bm25"
    has_spans = True

    def version(self) -> str:
        return f"bm25s {version('bm25s')}"

    def build(self, repo: Path, index_dir: Path) -> None:
        import bm25s

        size = int(self.params.get("chunk_lines", 50))
        self.chunks: list[tuple[str, int, int]] = []
        corpus: list[list[str]] = []
        for rel in list_files(repo):
            for start, end, text in chunk(read_lines(repo / rel), size):
                self.chunks.append((rel, start, end))
                corpus.append(tokenize(text))
        self.retriever = bm25s.BM25(
            k1=float(self.params.get("k1", 1.5)), b=float(self.params.get("b", 0.75))
        )
        self.retriever.index(corpus, show_progress=False)
        self.vocab = set(self.retriever.vocab_dict)
        self.retriever.save(str(index_dir), show_progress=False)

    def search(self, query: str, top_k: int) -> list[Hit]:
        tokens = [t for t in tokenize(query) if t in self.vocab]
        if not tokens or not self.chunks:
            return []
        k = min(top_k, len(self.chunks))
        docs, scores = self.retriever.retrieve([tokens], k=k, show_progress=False)
        out = []
        for idx, score in zip(docs[0], scores[0], strict=True):
            if score <= 0:
                continue
            f, s, e = self.chunks[int(idx)]
            out.append(Hit(f, s, e, float(score)))
        return out
