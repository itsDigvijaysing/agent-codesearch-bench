"""Run one adapter on one checkout in a fresh process: build, query, write raw hits.

Invoked by the runner as ``python -m csbench.worker SPEC.json`` so that memory is measured for
exactly one (tool, task) pair. Peak RSS is the maximum of this process's ``VmHWM`` (fresh after
exec, unlike ``ru_maxrss``, which keeps the parent's value) and ``ru_maxrss`` of the tool's
child processes; it is a per-process maximum, not a sum of concurrent processes.
"""

from __future__ import annotations

import json
import os
import resource
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")  # CPU only for any model-backed tool


def peak_rss_mib() -> float:
    hwm_kib = 0
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            hwm_kib = int(line.split()[1])
    children_kib = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return max(hwm_kib, children_kib) / 1024


def main(spec_path: str) -> int:
    from csbench.adapters import get_adapter

    spec = json.loads(Path(spec_path).read_text())
    out: dict = {"status": "error"}
    try:
        adapter = get_adapter(spec["adapter"])(**spec.get("params", {}))
        out["version"] = adapter.version()
        index_dir = Path(spec["index_dir"])
        index_dir.mkdir(parents=True, exist_ok=True)
        t0 = time.perf_counter()
        adapter.build(Path(spec["repo"]), index_dir)
        t1 = time.perf_counter()
        hits = adapter.search(spec["query"], int(spec["top_k"]))
        t2 = time.perf_counter()
        out.update(
            status="ok",
            build_s=t1 - t0,
            query_s=t2 - t1,
            has_spans=adapter.has_spans,
            hits=[asdict(h) for h in hits],
        )
    except Exception as exc:  # recorded, never dropped
        out["error"] = f"{type(exc).__name__}: {exc}"
        out["traceback"] = traceback.format_exc()[-4000:]
    out["peak_rss_mib"] = peak_rss_mib()
    Path(spec["out"]).write_text(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
