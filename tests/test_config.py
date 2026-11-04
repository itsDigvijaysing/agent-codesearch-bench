import dataclasses
from pathlib import Path

from csbench.config import Config

CFG = Path(__file__).parent.parent / "configs" / "v1.yaml"


def test_fingerprint_tracks_settings():
    cfg = Config.load(CFG)
    grep, bm25 = cfg.tools(["grep", "bm25"])
    assert cfg.fingerprint(grep) == cfg.fingerprint(grep)
    assert cfg.fingerprint(grep) != cfg.fingerprint(bm25)
    tuned = dataclasses.replace(grep, params={**grep.params, "context": 9})
    assert cfg.fingerprint(tuned) != cfg.fingerprint(grep)
    other = Config({**cfg.raw, "top_k": 20}, cfg.root)
    assert other.fingerprint(grep) != cfg.fingerprint(grep)
    budgets = Config({**cfg.raw, "metrics": {**cfg.raw["metrics"], "budgets": [1]}}, cfg.root)
    assert budgets.fingerprint(grep) != cfg.fingerprint(grep)
