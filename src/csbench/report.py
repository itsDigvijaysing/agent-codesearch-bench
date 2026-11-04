"""Aggregate per-task records into compact, committed result files.

Outputs in ``results/<run>/``:
  per_task/<tool>.jsonl.gz   every (tool, task) record, also used to resume across sessions
  summary.csv                means with 95% bootstrap CIs per tool and metric
  paired_vs_<baseline>.csv   paired bootstrap difference of each tool against the baseline
  summary.md                 the human-readable table
"""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

import numpy as np
import yaml

from csbench import plots
from csbench.config import Config
from csbench.metrics import bootstrap_ci, paired_bootstrap
from csbench.runner import committed_records, load_record, sample_ids

COST = ["tokens_returned", "query_s", "build_s", "index_mib", "peak_rss_mib"]
TABLE = [
    ("file_recall@1", "R@1"),
    ("file_recall@5", "R@5"),
    ("file_recall@10", "R@10"),
    ("file_precision@10", "P@10"),
    ("mrr", "MRR"),
    ("span_recall", "Span R"),
    ("span_precision", "Span P"),
    ("line_recall@2000tok", "R@2k tok"),
    ("line_recall@8000tok", "R@8k tok"),
]
COST_TABLE = [
    ("tokens_returned", "Tokens", "{:.0f}"),
    ("query_s", "Query s", "{:.2f}"),
    ("build_s", "Build s", "{:.1f}"),
    ("index_mib", "Index MiB", "{:.1f}"),
    ("peak_rss_mib", "RSS MiB", "{:.0f}"),
]


def collect(
    cfg: Config, tools: list[str] | None = None, use_committed: bool = True
) -> dict[str, list[dict]]:
    ids = sample_ids(cfg)
    out = {}
    for spec in cfg.tools(tools):
        if spec.status != "active":
            continue
        committed = committed_records(cfg, spec.name) if use_committed else {}
        recs = [load_record(cfg, spec, i, committed) for i in ids]
        out[spec.name] = [r for r in recs if r is not None]
    return out


def _value(rec: dict, key: str) -> float | None:
    if key == "index_mib":
        return rec["index_bytes"] / 2**20 if "index_bytes" in rec else None
    if key in rec.get("metrics", {}):
        if key == "tokens_returned" and rec["status"] != "ok":
            return None
        return rec["metrics"][key]
    return rec.get(key) if rec["status"] == "ok" else None


def summarize(cfg: Config, records: dict[str, list[dict]]) -> tuple[list[dict], list[dict], list]:
    """Return summary rows, paired rows and the tasks every tool has a record for."""
    empty = [t for t, recs in records.items() if not recs]
    if not records or empty:
        raise ValueError(f"no records to report for: {', '.join(empty) or 'any tool'}; run first")
    common = set.intersection(*({r["task_id"] for r in recs} for recs in records.values()))
    order = [i for i in sample_ids(cfg) if i in common]
    if not order:
        raise ValueError("the tools share no evaluated task; run them on the same tasks")
    boot = cfg["bootstrap"]
    kw = {"n_boot": boot["n_boot"], "seed": boot["seed"]}
    by_tool = {t: {r["task_id"]: r for r in recs} for t, recs in records.items()}
    quality = [k for k in next(iter(by_tool.values()))[order[0]]["metrics"] if k not in COST]
    rows, paired = [], []
    for tool, recs in by_tool.items():
        task_recs = [recs[i] for i in order]
        failed = sum(r["status"] != "ok" for r in task_recs)
        empty = sum(r["status"] == "ok" and r.get("n_hits", 1) == 0 for r in task_recs)
        versions = sorted({r["version"] for r in task_recs if r.get("version")})
        row = {
            "tool": tool,
            "version": "; ".join(versions),
            "n_tasks": len(order),
            "n_failed": failed,
            "failure_rate": failed / len(order),
            "n_empty": empty,
        }
        for key in quality + COST:
            vals = [v for v in (_value(r, key) for r in task_recs) if v is not None]
            mean, lo, hi = bootstrap_ci(np.array(vals), **kw) if vals else (None, None, None)
            row |= {f"{key}_mean": mean, f"{key}_lo": lo, f"{key}_hi": hi}
        rows.append(row)
        base = boot["baseline"]
        if tool != base and base in by_tool:
            for key in quality:
                a = [_value(recs[i], key) for i in order]
                b = [_value(by_tool[base][i], key) for i in order]
                if None in a or None in b:
                    continue
                paired.append(
                    {"tool": tool, "baseline": base, "metric": key}
                    | paired_bootstrap(np.array(a), np.array(b), **kw)
                )
    return rows, paired, order


def _fmt(row: dict, key: str, spec: str = "{:.3f}") -> str:
    if row.get(f"{key}_mean") is None:
        return "n/a"
    m, lo, hi = (row[f"{key}_{s}"] for s in ("mean", "lo", "hi"))
    return f"{spec.format(m)} [{spec.format(lo)}, {spec.format(hi)}]"


def markdown(
    cfg: Config,
    rows: list[dict],
    paired: list[dict],
    order: list[str],
    records: dict[str, list[dict]],
) -> str:
    d, b = cfg["dataset"], cfg["bootstrap"]
    lines = [
        f"# Results: {cfg.run_name}",
        "",
        f"Dataset `{d['repo_id']}` ({d['config']}) at revision `{d['revision'][:12]}`; "
        f"{len(order)} tasks from `{cfg['sample']['file']}`; top_k={cfg['top_k']}. "
        f"Means with 95% bootstrap CIs (B={b['n_boot']}, seed {b['seed']}); failed tasks "
        "score zero on quality metrics; Empty counts successful queries that returned nothing. "
        "n/a: not applicable (span metrics need line spans; token-budget recall needs returned "
        "code). Cost metrics are over successful tasks.",
        "",
        "## Retrieval quality",
        "",
        "| Tool | Version | Fail | Empty | " + " | ".join(h for _, h in TABLE) + " |",
        "|" + "---|" * (4 + len(TABLE)),
    ]
    for r in rows:
        cells = [_fmt(r, k) for k, _ in TABLE]
        fail, empty = f"{r['n_failed']}/{r['n_tasks']}", f"{r['n_empty']}/{r['n_tasks']}"
        lines.append(
            f"| {r['tool']} | {r['version']} | {fail} | {empty} | " + " | ".join(cells) + " |"
        )
    lines += [
        "",
        "## Cost",
        "",
        "| Tool | " + " | ".join(h for _, h, _ in COST_TABLE) + " |",
        "|" + "---|" * (1 + len(COST_TABLE)),
    ]
    for r in rows:
        lines.append(
            f"| {r['tool']} | " + " | ".join(_fmt(r, k, f) for k, _, f in COST_TABLE) + " |"
        )
    if paired:
        lines += [
            "",
            f"## Paired bootstrap against `{b['baseline']}`",
            "",
            "| Tool | Metric | Diff | 95% CI | p |",
            "|---|---|---|---|---|",
        ]
        for p in paired:
            if p["metric"] in ("file_recall@10", "mrr", "line_recall@8000tok"):
                lines.append(
                    f"| {p['tool']} | {p['metric']} | {p['diff']:+.3f} | "
                    f"[{p['ci_low']:+.3f}, {p['ci_high']:+.3f}] | {p['p_value']:.3f} |"
                )
    failures = [
        (t, r["task_id"], r.get("error", ""))
        for t, recs in records.items()
        for r in recs
        if r["task_id"] in order and r["status"] != "ok"
    ]
    lines += ["", "## Failures", ""]
    lines += [f"- `{t}` `{i}`: {e[:200]}" for t, i, e in failures] or ["None."]
    defs = yaml.safe_load((cfg.root / cfg["tools_file"]).read_text())["tools"]
    others = [(n, d) for n, d in defs.items() if d["status"] != "active"]
    if others:
        lines += ["", "## Tools not in this run", ""]
        lines += [f"- `{n}` ({d['status']}): {d.get('note', '')}" for n, d in others]
    return "\n".join(lines) + "\n"


README_START = "<!-- results:start (generated by `csbench report`) -->"
README_END = "<!-- results:end -->"


def headline(cfg: Config, rows: list[dict], order: list[str]) -> str:
    """Compact table for the README, generated so it never drifts from the summary."""
    lines = [
        "| Tool | File recall@10 | MRR | Line recall @ 8k tokens | Tokens returned | Failures |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        tokens = r.get("tokens_returned_mean")
        lines.append(
            f"| {r['tool']} ({r['version']}) | {_fmt(r, 'file_recall@10')} | {_fmt(r, 'mrr')} | "
            f"{_fmt(r, 'line_recall@8000tok')} | {'n/a' if tokens is None else f'{tokens:,.0f}'} "
            f"| {r['n_failed']}/{r['n_tasks']} |"
        )
    b = cfg["bootstrap"]
    lines += [
        "",
        f"Means over {len(order)} tasks with 95% bootstrap confidence intervals "
        f"(B = {b['n_boot']}, seed {b['seed']}). Full table: "
        f"[results/{cfg.run_name}/summary.md](results/{cfg.run_name}/summary.md).",
    ]
    return "\n".join(lines)


def update_readme(cfg: Config, table: str) -> bool:
    path = cfg.root / "README.md"
    text = path.read_text() if path.exists() else ""
    if README_START not in text or README_END not in text:
        return False
    head, rest = text.split(README_START, 1)
    _, tail = rest.split(README_END, 1)
    path.write_text(f"{head}{README_START}\n{table}\n{README_END}{tail}")
    return True


def write(
    cfg: Config,
    tools: list[str] | None = None,
    use_committed: bool = True,
    readme: bool = True,
) -> Path:
    records = collect(cfg, tools, use_committed)
    out = cfg.path("results") / cfg.run_name
    (out / "per_task").mkdir(parents=True, exist_ok=True)
    for tool, recs in records.items():
        data = "".join(json.dumps(r, sort_keys=True) + "\n" for r in recs).encode()
        # mtime=0 and no stored name keep the file byte-identical across regenerations
        with (out / "per_task" / f"{tool}.jsonl.gz").open("wb") as raw:
            raw.write(gzip.compress(data, compresslevel=9, mtime=0))
    rows, paired, order = summarize(cfg, records)
    _csv(out / "summary.csv", rows)
    _csv(out / f"paired_vs_{cfg['bootstrap']['baseline']}.csv", paired)
    (out / "summary.md").write_text(markdown(cfg, rows, paired, order, records))
    plots.write(rows, len(order), out / "plots")
    if readme:
        update_readme(cfg, headline(cfg, rows, order))
    return out


def _csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})
