import pytest

from csbench.config import Config
from csbench.report import summarize


def test_summarize_rejects_missing_records(tmp_path):
    cfg = Config({"sample": {"file": "s.txt"}, "bootstrap": {}}, tmp_path)
    (tmp_path / "s.txt").write_text("t1\n")
    with pytest.raises(ValueError, match="bm25"):
        summarize(cfg, {"grep": [{"task_id": "t1"}], "bm25": []})
    with pytest.raises(ValueError, match="share no"):
        summarize(cfg, {"grep": [{"task_id": "t1"}], "bm25": [{"task_id": "t2"}]})
