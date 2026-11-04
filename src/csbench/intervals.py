"""Inclusive line-interval operations.

Ported from ContextBench ``contextbench/core/intervals.py`` and the line-level helpers in
``contextbench/metrics/compute.py`` (Apache-2.0, https://github.com/EuniAI/ContextBench,
commit 1436c28a8eb95496da4ea69ad458b9f8a8eb7d61), so span scores match its line metric.
"""

from __future__ import annotations

Interval = tuple[int, int]  # (start_line, end_line), 1-based, inclusive


def merge(intervals: list[Interval]) -> list[Interval]:
    """Merge overlapping or adjacent intervals."""
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 1:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def length(intervals: list[Interval]) -> int:
    return sum(end - start + 1 for start, end in merge(intervals))


def intersect(a: list[Interval], b: list[Interval]) -> list[Interval]:
    a_m, b_m = merge(a), merge(b)
    out: list[Interval] = []
    i = j = 0
    while i < len(a_m) and j < len(b_m):
        lo, hi = max(a_m[i][0], b_m[j][0]), min(a_m[i][1], b_m[j][1])
        if lo <= hi:
            out.append((lo, hi))
        if a_m[i][1] < b_m[j][1]:
            i += 1
        elif b_m[j][1] < a_m[i][1]:
            j += 1
        else:
            i += 1
            j += 1
    return out


def total_lines(by_file: dict[str, list[Interval]]) -> int:
    return sum(length(iv) for iv in by_file.values())


def intersection_lines(a: dict[str, list[Interval]], b: dict[str, list[Interval]]) -> int:
    return sum(length(intersect(a[f], b[f])) for f in a.keys() & b.keys())
