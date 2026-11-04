import random

from csbench.dataset import Task
from csbench.sample import allocate, select


def make(repo, i, lang="python"):
    return Task(f"{repo}-{i}", repo, "", lang, "", "", "", {})


def test_allocate_water_fills():
    alloc = allocate({"a": 3, "b": 50, "c": 50}, 20, random.Random(0))
    assert alloc["a"] == 3 and sum(alloc.values()) == 20
    assert abs(alloc["b"] - alloc["c"]) <= 1


def test_select_is_deterministic_and_filters():
    tasks = [
        make(r, i) for r, n in [("r1", 30), ("r2", 20), ("r3", 5), ("r4", 2)] for i in range(n)
    ] + [make("js", i, "javascript") for i in range(40)]
    ids = select(tasks, language="python", max_repos=3, n_tasks=20, seed=0)
    assert ids == select(tasks, language="python", max_repos=3, n_tasks=20, seed=0)
    assert len(ids) == len(set(ids)) == 20
    repos = {i.rsplit("-", 1)[0] for i in ids}
    assert repos == {"r1", "r2", "r3"}
    assert sum(i.startswith("r3-") for i in ids) == 5
