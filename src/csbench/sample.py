"""Deterministic v1 task sample.

Rule (documented in README "Method"):
1. Keep tasks whose ``language`` is ``python``.
2. Rank repositories by number of Python tasks (descending, ties by name) and keep the top
   ``max_repos``.
3. Allocate ``n_tasks`` across those repositories by water-filling: every repository gets the
   same quota, a repository with fewer tasks contributes all of them, and the freed seats are
   redistributed. Seats left over by integer division go one each to repositories with spare
   capacity, in an order drawn from ``random.Random(seed)``.
4. Inside each repository (in name order) draw the allocated task ids with the same generator
   from the sorted id list.
5. Shuffle the selected ids with the same generator, so every prefix is also a seeded random
   subset (used for smoke runs such as ``--limit 10``).
"""

from __future__ import annotations

import random
from collections import Counter

from csbench.dataset import Task


def allocate(counts: dict[str, int], n_tasks: int, rng: random.Random) -> dict[str, int]:
    if n_tasks > sum(counts.values()):
        raise ValueError(f"cannot draw {n_tasks} tasks from {sum(counts.values())}")
    alloc = dict.fromkeys(counts, 0)
    open_repos = sorted(counts)
    remaining = n_tasks
    while remaining and open_repos:
        quota = remaining // len(open_repos)
        if quota == 0:
            for repo in rng.sample(open_repos, remaining):
                alloc[repo] += 1
            break
        for repo in list(open_repos):
            take = min(quota, counts[repo] - alloc[repo])
            alloc[repo] += take
            remaining -= take
            if alloc[repo] == counts[repo]:
                open_repos.remove(repo)
    return alloc


def select(
    tasks: list[Task], *, language: str, max_repos: int, n_tasks: int, seed: int
) -> list[str]:
    pool = [t for t in tasks if t.language == language]
    counts = Counter(t.repo for t in pool)
    top = sorted(counts, key=lambda r: (-counts[r], r))[:max_repos]
    rng = random.Random(seed)
    alloc = allocate({r: counts[r] for r in top}, n_tasks, rng)
    chosen: list[str] = []
    for repo in sorted(top):
        ids = sorted(t.instance_id for t in pool if t.repo == repo)
        chosen.extend(rng.sample(ids, alloc[repo]))
    rng.shuffle(chosen)
    return chosen
