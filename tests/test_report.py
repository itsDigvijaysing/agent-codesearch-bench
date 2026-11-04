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
