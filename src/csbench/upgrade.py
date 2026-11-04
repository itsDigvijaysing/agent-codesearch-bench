"""Upgrade the pinned versions of the tools under test (not the grep and BM25 baselines).

For every active tool with its own environment and a ``name==version`` pin, look up the latest
release on PyPI; when it is newer, rewrite the pin in ``configs/tools.yaml`` and regenerate the
tool's lock file. Changed fingerprints then make the runner recompute only those tools.
"""

from __future__ import annotations

import json
import re
import subprocess
import urllib.request
from dataclasses import replace

from csbench.config import Config, ToolSpec
from csbench.runner import lock_env, tool_python


class NeedsReview(RuntimeError):
    """An upgrade changed a default that a pinned parameter relies on."""


def latest_version(dist: str) -> str:
    with urllib.request.urlopen(f"https://pypi.org/pypi/{dist}/json", timeout=30) as resp:
        return json.load(resp)["info"]["version"]


def _check_defaults(cfg: Config, spec: ToolSpec) -> None:
    """semble's default model is pinned by revision; a new default needs a maintainer."""
    if spec.adapter != "semble":
        return
    code = "from semble.utils import DEFAULT_MODEL_NAME as m; print(m)"
    out = subprocess.run([tool_python(cfg, spec), "-c", code], capture_output=True, text=True)
    default = out.stdout.strip()
    if out.returncode != 0 or default != spec.params.get("model"):
        raise NeedsReview(
            f"{spec.name}: default model is now {default!r}, configured "
            f"{spec.params.get('model')!r}; pin the new model and revision in tools.yaml"
        )


def upgrade(cfg: Config, tools: list[str] | None = None) -> list[tuple[str, str, str]]:
    path = cfg.root / cfg["tools_file"]
    changes = []
    for spec in cfg.tools(tools):
        if spec.status != "active" or not spec.env or "==" not in spec.pin:
            continue
        dist, old = spec.pin.split("==", 1)
        new = latest_version(dist)
        if new == old:
            continue
        text = path.read_text()
        pattern = re.compile(rf'(pin:\s*"){re.escape(spec.pin)}(")')
        if not pattern.search(text):
            raise ValueError(f"pin {spec.pin!r} not found in {path}")
        path.write_text(pattern.sub(rf"\g<1>{dist}=={new}\g<2>", text, count=1))
        updated = replace(spec, pin=f"{dist}=={new}")
        lock_env(cfg, updated)
        _check_defaults(cfg, updated)
        changes.append((spec.name, old, new))
    return changes
