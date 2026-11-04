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

    def fingerprint(self, top_k: int) -> str:
        """Changes whenever the result could change: adapter, pinned version, params, top_k."""
        blob = json.dumps([self.adapter, self.pin, self.params, top_k], sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:12]


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
