import pytest

from csbench.config import Config
from csbench.report import README_END, README_START, summarize, update_readme


def test_summarize_rejects_missing_records(tmp_path):
    cfg = Config({"sample": {"file": "s.txt"}, "bootstrap": {}}, tmp_path)
    (tmp_path / "s.txt").write_text("t1\n")
    with pytest.raises(ValueError, match="bm25"):
        summarize(cfg, {"grep": [{"task_id": "t1"}], "bm25": []})
    with pytest.raises(ValueError, match="share no"):
        summarize(cfg, {"grep": [{"task_id": "t1"}], "bm25": [{"task_id": "t2"}]})


def test_update_readme_replaces_only_marked_block(tmp_path):
    cfg = Config({}, tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(f"intro\n{README_START}\nold\n{README_END}\noutro\n")
    assert update_readme(cfg, "new table")
    assert readme.read_text() == f"intro\n{README_START}\nnew table\n{README_END}\noutro\n"
    readme.write_text("no markers\n")
    assert not update_readme(cfg, "x") and readme.read_text() == "no markers\n"


def test_plot_tick_formatters():
    from csbench.plots import fmt_seconds, fmt_tokens

    assert [fmt_tokens(v) for v in (500, 2000, 50000)] == ["500", "2K", "50K"]
    assert [fmt_seconds(v) for v in (0.002, 0.05, 2)] == ["2 ms", "50 ms", "2 s"]


def test_headline_is_a_simple_percentage_table():
    from types import SimpleNamespace

    from csbench.report import headline

    rows = [{"tool": "semble", "version": "semble 0.7.2", "file_recall@10_mean": 0.62,
             "line_recall@8000tok_mean": None, "tokens_returned_mean": 3344.2, "n_failed": 0}]
    text = headline(SimpleNamespace(run_name="v1"), rows, ["t"] * 100)
    assert "| semble (semble 0.7.2) | 62% | n/a | 3,344 |" in text
    assert "Means over 100 tasks (0 failed queries)" in text
