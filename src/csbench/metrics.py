"""Per-task retrieval metrics and bootstrap statistics.

Span metrics follow ContextBench's line-level coverage/precision (inclusive line intervals,
merged per file). One deviation: an empty prediction scores precision 0, not 1, so a tool
that returns nothing is never rewarded.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from csbench.intervals import Interval, intersection_lines, merge, total_lines


@dataclass(frozen=True)
class ResolvedHit:
    """A returned result resolved against the checkout: lines and per-line token counts."""

    file: str
    start: int
    end: int
    line_tokens: tuple[int, ...]

    @property
    def tokens(self) -> int:
        return sum(self.line_tokens)


def ranked_files(hits: list[ResolvedHit]) -> list[str]:
    seen: dict[str, None] = {}
    for h in hits:
        seen.setdefault(h.file, None)
    return list(seen)


def _lines(hits: list[ResolvedHit]) -> dict[str, list[Interval]]:
    out: dict[str, list[Interval]] = {}
    for h in hits:
        if h.end >= h.start:
            out.setdefault(h.file, []).append((h.start, h.end))
    return {f: merge(iv) for f, iv in out.items()}


def _budget_prefix(hits: list[ResolvedHit], budget: int) -> list[ResolvedHit]:
    """Hits in rank order until ``budget`` tokens; the overflowing hit keeps its leading lines."""
    out: list[ResolvedHit] = []
    used = 0
    for h in hits:
        if used + h.tokens <= budget:
            out.append(h)
            used += h.tokens
            continue
        n = 0
        for t in h.line_tokens:
            if used + t > budget:
                break
            used += t
            n += 1
        if n:
            out.append(ResolvedHit(h.file, h.start, h.start + n - 1, h.line_tokens[:n]))
        break
    return out


def task_metrics(
    gold: dict[str, list[Interval]],
    hits: list[ResolvedHit],
    *,
    ks: tuple[int, ...] = (1, 5, 10),
    precision_ks: tuple[int, ...] = (5, 10),
    budgets: tuple[int, ...] = (2000, 8000),
    has_spans: bool = True,
    returns_code: bool = True,
    output_tokens: int | None = None,
) -> dict[str, float | None]:
    """Metrics for one task.

    ``has_spans=False`` (results are files or bare locations) reports span metrics as None.
    ``returns_code=False`` (the tool returns locations, not code) reports token-budget recall
    as None and uses ``output_tokens``, the size of the tool's own output, as tokens returned.
    """
    gold_files = set(gold)
    files = ranked_files(hits)
    m: dict[str, float | None] = {}
    for k in ks:
        m[f"file_recall@{k}"] = len(set(files[:k]) & gold_files) / len(gold_files)
    for k in precision_ks:
        m[f"file_precision@{k}"] = len(set(files[:k]) & gold_files) / k
    m["mrr"] = next((1.0 / (i + 1) for i, f in enumerate(files) if f in gold_files), 0.0)

    gold_total = total_lines(gold)
    pred = _lines(hits)
    if has_spans:
        inter = intersection_lines(pred, gold)
        pred_total = total_lines(pred)
        m["span_recall"] = inter / gold_total if gold_total else 1.0
        m["span_precision"] = inter / pred_total if pred_total else 0.0
    else:
        m["span_recall"] = m["span_precision"] = None
    if not returns_code:
        m["tokens_returned"] = float(output_tokens or 0)
        m |= {f"line_recall@{b}tok": None for b in budgets}
        return m
    m["tokens_returned"] = float(sum(h.tokens for h in hits))
    for b in budgets:
        inter = intersection_lines(_lines(_budget_prefix(hits, b)), gold)
        m[f"line_recall@{b}tok"] = inter / gold_total if gold_total else 1.0
    return m


def zero_metrics(template: dict[str, float | None]) -> dict[str, float | None]:
    """Score a failed task as zero on every quality metric (tokens returned 0)."""
    return {k: (None if v is None else 0.0) for k, v in template.items()}


def _boot_means(values: np.ndarray, n_boot: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(n_boot, len(values)))
    return values[idx].mean(axis=1)


def bootstrap_ci(
    values: np.ndarray, *, n_boot: int = 1000, seed: int = 42, alpha: float = 0.05
) -> tuple[float, float, float]:
    """Mean and percentile bootstrap CI over tasks."""
    values = np.asarray(values, dtype=float)
    lo, hi = np.quantile(_boot_means(values, n_boot, seed), [alpha / 2, 1 - alpha / 2])
    return float(values.mean()), float(lo), float(hi)


def paired_bootstrap(
    a: np.ndarray, b: np.ndarray, *, n_boot: int = 1000, seed: int = 42, alpha: float = 0.05
) -> dict[str, float]:
    """Mean difference a - b over the same tasks, its CI and a two-sided bootstrap p-value."""
    diff = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    means = _boot_means(diff, n_boot, seed)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    p = min(1.0, 2 * min(float((means <= 0).mean()), float((means >= 0).mean())))
    return {"diff": float(diff.mean()), "ci_low": float(lo), "ci_high": float(hi), "p_value": p}
