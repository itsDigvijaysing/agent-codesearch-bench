import shutil
from pathlib import Path

import pytest

from csbench import upgrade
from csbench.config import Config

ROOT = Path(__file__).parent.parent


@pytest.fixture
def cfg(tmp_path):
    shutil.copytree(ROOT / "configs", tmp_path / "configs")
    return Config.load(tmp_path / "configs" / "v1.yaml")


def test_upgrade_rewrites_only_changed_pins(cfg, monkeypatch):
    latest = {"semble": "9.9.9"}
    monkeypatch.setattr(upgrade, "latest_version", lambda d: latest.get(d, _current(cfg, d)))
    locked = []
    monkeypatch.setattr(upgrade, "lock_env", lambda c, s: locked.append(s.pin))
    monkeypatch.setattr(upgrade, "_check_defaults", lambda c, s: None)
    assert upgrade.upgrade(cfg) == [("semble", "0.7.2", "9.9.9")]
    assert locked == ["semble==9.9.9"]
    text = (cfg.root / "configs" / "tools.yaml").read_text()
    assert 'pin: "semble==9.9.9"' in text and 'pin: "bm25s==0.3.16"' in text


def test_upgrade_noop_when_current(cfg, monkeypatch):
    monkeypatch.setattr(upgrade, "latest_version", lambda d: _current(cfg, d))
    assert upgrade.upgrade(cfg) == []


def _current(cfg, dist):
    for spec in cfg.tools():
        if spec.pin.startswith(f"{dist}=="):
            return spec.pin.split("==")[1]
    raise KeyError(dist)
