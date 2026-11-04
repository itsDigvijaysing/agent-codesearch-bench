import random

from csbench.dataset import Task
from csbench.sample import allocate, select, select_hard


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


def make_multi(repo, i, n_files):
    return Task(
        f"{repo}-{i}", repo, "", "go", "", "", "", {f"f{k}.go": [(1, 2)] for k in range(n_files)}
    )


def test_select_hard_rule():
    tasks = [make_multi("big", i, 3) for i in range(8)] + [make_multi("big", 9, 2)]
    tasks += [make_multi("small", i, 4) for i in range(5)] + [make_multi("big2", 0, 5)]
    kw = dict(
        repo_files={"big": 3000, "big2": 2500, "small": 100},
        min_gold_files=3,
        min_repo_files=2500,
        per_repo=5,
        seed=0,
    )
    ids = select_hard(tasks, exclude={"big-0"}, **kw)
    assert ids == select_hard(tasks, exclude={"big-0"}, **kw)
    assert len(ids) == 6 and "big2-0" in ids
    assert not any(i.startswith("small") or i in ("big-0", "big-9") for i in ids)
