"""Run configuration (``configs/v1.yaml``) and pinned tool definitions (``configs/tools.yaml``)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ToolSpec:
    name: str
    adapter: str
    pin: str
    params: dict
    status: str  # "active", "planned", "excluded", "track_b"
    note: str = ""


@dataclass(frozen=True)
class Config:
    raw: dict
    root: Path

    @classmethod
    def load(cls, path: str | Path) -> Config:
        path = Path(path).resolve()
        return cls(yaml.safe_load(path.read_text()), path.parent.parent)

    def __getitem__(self, key: str):
        return self.raw[key]

    def path(self, key: str) -> Path:
        return self.root / self.raw["paths"][key]

    def fingerprint(self, spec: ToolSpec) -> str:
        """Changes whenever a stored result could change, so stale records are never reused.

        Covers the tool definition, top_k, metric settings, dataset revision, and the source of
        the adapter, the shared corpus rule and the metric code.
        """
        pkg = Path(__file__).parent
        sources = [
            pkg / "adapters" / "base.py",
            pkg / "adapters" / f"{spec.adapter.replace('-', '_')}.py",
            pkg / "files.py",
            pkg / "intervals.py",
            pkg / "metrics.py",
        ]
        settings = [spec.adapter, spec.pin, spec.params, self.raw["top_k"], self.raw["metrics"]]
        h = hashlib.sha256(
            json.dumps(settings + [self.raw["dataset"]["revision"]], sort_keys=True).encode()
        )
        for src in sources:
            if src.exists():
                h.update(src.read_text().replace("\r\n", "\n").encode())
        return h.hexdigest()[:12]

    @property
    def run_name(self) -> str:
        return self.raw["run"]

    def tools(self, names: list[str] | None = None) -> list[ToolSpec]:
        defs = yaml.safe_load((self.root / self.raw["tools_file"]).read_text())["tools"]
        wanted = names or self.raw["tools"]
        out = []
        for name in wanted:
            d = defs[name]
            out.append(
                ToolSpec(
                    name=name,
                    adapter=d["adapter"],
                    pin=d["pin"],
                    params=d.get("params") or {},
                    status=d["status"],
                    note=d.get("note", ""),
                )
            )
        return out
