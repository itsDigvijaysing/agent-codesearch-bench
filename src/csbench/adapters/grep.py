"""grep baseline: ripgrep over identifiers extracted from the issue text.

Term extraction rule (applied to the problem statement with URLs and e-mail addresses removed,
in this order, case-sensitive):
  1. file paths: ``word/word.ext`` or ``word.ext`` with a source/doc extension;
  2. dotted names: ``a.b`` or longer chains of identifiers, except web domains (``www.`` prefix
     or a final component that is a common top-level domain) and prose abbreviations whose
     components are all single letters (``e.g``, ``i.e``);
  3. CamelCase and camelCase identifiers;
  4. snake_case identifiers (contain ``_``, includes dunders);
  5. quoted strings of 3-80 chars without a newline, in backticks, or in single/double quotes
     not adjoining a word character (so prose apostrophes are skipped), except a single plain
     word such as ``'where'``, which is English rather than an identifier.
Terms shorter than 3 characters are dropped, duplicates removed keeping first occurrence, and
at most ``max_terms`` (default 64) are kept. ripgrep searches all terms as fixed strings in one
pass over the checkout (hidden files included, ``.git`` excluded, ``.gitignore`` respected,
files over 1 MB skipped). With ``rank: hits`` (default) files are ranked by total hit count,
ties broken by number of distinct terms matched, then path; ``rank: distinct`` sorts by
distinct terms matched first, then hit count, then path. Each returned file contributes its
hit lines with ``context`` lines (default 3) on each side, merged.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

from csbench.adapters.base import Adapter, Hit
from csbench.intervals import merge

_EXT = r"(?:py|pyi|pyx|pxd|c|h|cpp|js|ts|rst|md|txt|cfg|ini|toml|yaml|yml|json|html|css)"
PATTERNS = [
    re.compile(rf"(?<![\w/.-])(?:[\w-]+/)*[\w-]+\.{_EXT}\b"),
    re.compile(r"\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+\b"),
    re.compile(r"\b(?:[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+|[a-z][a-z0-9]*(?:[A-Z][a-z0-9]*)+)\b"),
    re.compile(r"\b_*[A-Za-z][A-Za-z0-9]*(?:_+[A-Za-z0-9]+)+_*\b|\b__\w+__\b"),
    re.compile(r"`([^`\n]{3,80})`|(?<!\w)'([^'\n]{3,80})'(?!\w)|(?<!\w)\"([^\"\n]{3,80})\"(?!\w)"),
]


_URL = re.compile(r"\b(?:https?|ftp)://\S+|\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_TLD = {"com", "org", "net", "io", "edu", "gov", "info", "dev", "uk", "de", "fr", "ch", "jp"}
_PLAIN_WORD = re.compile(r"[A-Za-z]+")
_DOTTED = 1
_QUOTED = 4


def _keep(order: int, term: str) -> bool:
    if len(term) < 3:
        return False
    if order == _DOTTED:
        parts = term.split(".")
        if parts[0] == "www" or parts[-1] in _TLD or all(len(p) == 1 for p in parts):
            return False
    return not (order == _QUOTED and _PLAIN_WORD.fullmatch(term))


def extract_terms(text: str, max_terms: int = 64) -> list[str]:
    text = _URL.sub(" ", text)
    found: list[tuple[int, int, str]] = []
    for order, pattern in enumerate(PATTERNS):
        for m in pattern.finditer(text):
            term = next((g for g in m.groups() if g), None) if m.groups() else m.group(0)
            if term and _keep(order, term.strip()):
                found.append((order, m.start(), term.strip()))
    terms: dict[str, None] = {}
    for _, _, term in sorted(found):
        terms.setdefault(term, None)
    return list(terms)[:max_terms]


class GrepAdapter(Adapter):
    name = "grep"
    has_spans = True

    def version(self) -> str:
        out = subprocess.run(["rg", "--version"], capture_output=True, text=True, check=True)
        return out.stdout.split("\n", 1)[0].strip()

    def build(self, repo: Path, index_dir: Path) -> None:
        self.repo = repo

    def search(self, query: str, top_k: int) -> list[Hit]:
        terms = extract_terms(query, int(self.params.get("max_terms", 64)))
        if not terms:
            return []
        context = int(self.params.get("context", 3))
        cmd = [
            "rg",
            "--json",
            "--fixed-strings",
            "--case-sensitive",
            "--hidden",
            "--glob",
            "!.git",
            "--max-filesize",
            "1M",
        ]
        for t in terms:
            cmd += ["-e", t]
        proc = subprocess.run(cmd + ["--", "."], cwd=self.repo, capture_output=True, text=True)
        if proc.returncode not in (0, 1):
            raise RuntimeError(f"rg failed: {proc.stderr.strip()[:500]}")
        hits: dict[str, int] = defaultdict(int)
        distinct: dict[str, set[str]] = defaultdict(set)
        lines: dict[str, list[int]] = defaultdict(list)
        for raw in proc.stdout.splitlines():
            ev = json.loads(raw)
            if ev["type"] != "match":
                continue
            data = ev["data"]
            path = data["path"].get("text")
            if path is None:
                continue
            path = path[2:] if path.startswith("./") else path
            subs = data["submatches"]
            hits[path] += len(subs)
            distinct[path].update(s["match"].get("text", "") for s in subs)
            lines[path].append(data["line_number"])
        if self.params.get("rank", "hits") == "distinct":
            ranked = sorted(hits, key=lambda f: (-len(distinct[f]), -hits[f], f))[:top_k]
        else:
            ranked = sorted(hits, key=lambda f: (-hits[f], -len(distinct[f]), f))[:top_k]
        out: list[Hit] = []
        for f in ranked:
            windows = merge([(max(1, n - context), n + context) for n in lines[f]])
            out.extend(Hit(f, s, e, float(hits[f])) for s, e in windows)
        return out
