import numpy as np
import pytest

from csbench.metrics import (
    ResolvedHit,
    bootstrap_ci,
    paired_bootstrap,
    ranked_files,
    task_metrics,
    zero_metrics,
)


def hit(f, s, e, tok=1):
    return ResolvedHit(f, s, e, tuple([tok] * (e - s + 1)))


GOLD = {"a.py": [(10, 19)], "b.py": [(1, 10)]}  # 20 gold lines over 2 files


def test_ranked_files_dedupes_in_order():
    assert ranked_files([hit("x", 1, 1), hit("a.py", 1, 1), hit("x", 5, 5)]) == ["x", "a.py"]


def test_file_metrics():
    hits = [hit("x.py", 1, 5), hit("a.py", 10, 14), hit("c.py", 1, 1), hit("b.py", 1, 1)]
    m = task_metrics(GOLD, hits, ks=(1, 5, 10), precision_ks=(5, 10))
    assert m["file_recall@1"] == 0
    assert m["file_recall@5"] == m["file_recall@10"] == 1
    assert m["file_precision@5"] == pytest.approx(2 / 5)
    assert m["file_precision@10"] == pytest.approx(2 / 10)
    assert m["mrr"] == pytest.approx(0.5)


def test_span_metrics():
    hits = [hit("a.py", 15, 24), hit("a.py", 20, 24)]  # overlap counted once
    m = task_metrics(GOLD, hits)
    assert m["span_recall"] == pytest.approx(5 / 20)
    assert m["span_precision"] == pytest.approx(5 / 10)
    assert m["tokens_returned"] == 15


def test_empty_prediction_scores_zero():
    m = task_metrics(GOLD, [])
    assert m["mrr"] == 0 and m["file_recall@10"] == 0
    assert m["span_recall"] == 0 and m["span_precision"] == 0


def test_no_spans_reports_none():
    m = task_metrics(GOLD, [hit("a.py", 1, 30)], has_spans=False)
    assert m["span_recall"] is None and m["span_precision"] is None
    assert zero_metrics(m)["span_recall"] is None
    assert zero_metrics(m)["file_recall@1"] == 0


def test_budget_truncates_overflowing_hit():
    hits = [hit("a.py", 10, 19, tok=100), hit("b.py", 1, 10, tok=100)]  # 1000 tokens each
    m = task_metrics(GOLD, hits, budgets=(500, 1000, 2000))
    assert m["line_recall@500tok"] == pytest.approx(5 / 20)
    assert m["line_recall@1000tok"] == pytest.approx(10 / 20)
    assert m["line_recall@2000tok"] == pytest.approx(1.0)


def test_budget_stops_at_first_overflow():
    hits = [hit("x.py", 1, 1, tok=5000), hit("a.py", 10, 19, tok=1)]
    m = task_metrics(GOLD, hits, budgets=(2000,))
    assert m["line_recall@2000tok"] == 0


def test_bootstrap_ci_is_deterministic_and_brackets_mean():
    v = np.arange(100) / 100
    mean, lo, hi = bootstrap_ci(v, n_boot=1000, seed=42)
    assert lo < mean < hi
    assert (mean, lo, hi) == bootstrap_ci(v, n_boot=1000, seed=42)
    assert bootstrap_ci(np.ones(10)) == (1.0, 1.0, 1.0)


def test_paired_bootstrap():
    rng = np.random.default_rng(0)
    b = rng.random(100)
    better = paired_bootstrap(b + 0.2, b)
    assert better["diff"] == pytest.approx(0.2)
    assert better["ci_low"] > 0 and better["p_value"] == 0
    same = paired_bootstrap(b, b)
    assert same["diff"] == 0 and same["p_value"] == 1
