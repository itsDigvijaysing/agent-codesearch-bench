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
