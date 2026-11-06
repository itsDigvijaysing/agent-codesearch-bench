import csv
import gzip
import json

from csbench import plots

ROW_KEYS = ("file_recall@10", "line_recall@8000tok", "tokens_returned", "query_s")


def _row(tool, base, with_lines=True):
    row = {"tool": tool, "n_tasks": 2}
    for i, key in enumerate(ROW_KEYS):
        mean = base / (i + 1) if with_lines or key != "line_recall@8000tok" else None
        lo = hi = None if mean is None else mean
        row.update({f"{key}_mean": mean, f"{key}_lo": lo, f"{key}_hi": hi})
    return row


def test_write_adds_files_vs_lines(tmp_path):
    rows = [_row("grep", 0.3), _row("graphify", 0.4, with_lines=False)]
    names = {p.name for p in plots.write(rows, 2, tmp_path)}
    assert {"files_vs_lines_light.png", "files_vs_lines_dark.png"} <= names
    assert all((tmp_path / n).stat().st_size > 0 for n in names)


def test_write_overview_uses_committed_results(tmp_path):
    assert plots.write_overview(tmp_path) == []
    for run, base in (("v1", 0.6), ("hard", 0.3)):
        (tmp_path / run).mkdir()
        rows = [_row("grep", base), _row("semble", base + 0.1)]
        with (tmp_path / run / "summary.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    (tmp_path / plots.TRACKB_RUN).mkdir()
    recs = [
        {
            "arm": arm,
            "task_id": t,
            "ok": True,
            "file_recall@10": 0.8,
            "duration_s": 10.0 + i,
            "cost_usd": 0.007 + i / 1000,
        }
        for arm in ("baseline", "semble")
        for i, t in enumerate(("t1", "t2"))
    ]
    data = "".join(json.dumps(r) + "\n" for r in recs).encode()
    (tmp_path / plots.TRACKB_RUN / "records.jsonl.gz").write_bytes(gzip.compress(data))
    names = sorted(p.name for p in plots.write_overview(tmp_path))
    assert names == [
        "trackb_dark.png",
        "trackb_light.png",
        "v1_vs_hard_dark.png",
        "v1_vs_hard_light.png",
    ]
