"""Track B: an agent localizes the code an issue needs, with and without each tool.

Protocol (``configs/trackb.yaml``): every arm gets the same prompt at the task's base commit;
arms differ only in a project setup line and the tool's own documented agent instructions,
given as CLAUDE.md project instructions at the top of the prompt. The
agent ends with a JSON list of locations, scored against the gold context with the Track A
file and span metrics. Cost comes from the session's own result record (tokens, turns, time).

Sessions ran in cloud sessions through the session API (40-task run) or locally with
``csbench trackb-local`` (:mod:`csbench.trackb_local`); each finished session is saved as
``.cache/trackb/<run>/<arm>/<task>.json`` with the fields of :data:`RECORD_FIELDS`.
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import numpy as np
import yaml

from csbench.dataset import Task, load_tasks, normalize_path
from csbench.metrics import ResolvedHit, bootstrap_ci, paired_bootstrap, task_metrics

RECORD_FIELDS = (
    "task_id", "arm", "session_id", "model", "status", "result_text",
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens",
    "num_turns", "duration_s", "cost_usd", "web_requests",
    "permission_denials", "tool_calls",
)  # fmt: skip
# tool_calls: number of the arm tool's commands the agent actually ran (None for baseline or
# when not collected); permission_denials: tool calls the session's permission check blocked.
QUALITY = ["file_recall@1", "file_recall@5", "file_recall@10", "mrr", "span_recall",
           "span_precision"]  # fmt: skip
EXTRA_FIELDS = ("graph_built", "resumed_after_limit", "result_events", "harness", "prebuild_s",
                "prebuild_ok", "wall_s", "network_commands", "subagent_calls",
                "claude_code_version")  # fmt: skip
COST = ["total_tokens", "output_tokens", "num_turns", "duration_s", "cost_usd"]
CLAUDE_MD_HEADING = "Contents of CLAUDE.md (project instructions, checked into the codebase):"
_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def load_config(path: str | Path, run: str) -> tuple[dict, Path]:
    """The protocol with one named run's model, task count and arms resolved."""
    path = Path(path).resolve()
    cfg = yaml.safe_load(path.read_text())
    spec = cfg["runs"][run]
    arms = spec.get("arms") or list(cfg["arms"])
    cfg |= {
        "run": run,
        "model": spec["model"],
        "limit": spec.get("limit"),
        "sample": spec.get("sample", cfg["sample"]),
        "prebuild": spec.get("prebuild", False),
    }
    cfg["arms"] = {a: cfg["arms"][a] for a in arms}
    return cfg, path.parent.parent


def tasks(cfg: dict, root: Path, parquet: Path) -> list[Task]:
    by_id = {t.instance_id: t for t in load_tasks(parquet)}
    ids = [i for i in (root / cfg["sample"]).read_text().split() if i]
    return [by_id[i] for i in ids[: cfg.get("limit")]]


def clean(text: str) -> str:
    """Line endings to LF and no trailing spaces, so the prompt survives the session API intact."""
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n")).strip()


def session_request(cfg: dict, root: Path, task: Task, arm: str) -> dict:
    """Everything needed to start one session, exactly as the protocol specifies."""
    spec = cfg["arms"][arm]
    prompt = cfg["prompt"].format(
        repo=task.repo,
        setup="" if cfg.get("prebuild") else spec["setup"],  # prebuilt: the index exists
        max_locations=cfg["max_locations"],
        issue=clean(task.problem_statement),
    )
    if spec["instructions"]:
        # Delivered as project instructions, where each tool's own installer puts them
        # (CLAUDE.md). The session API ignores append_system_prompt (verified with a probe).
        text = re.sub(r"<!--.*?-->\s*", "", (root / spec["instructions"]).read_text(), flags=re.S)
        prompt = f"{CLAUDE_MD_HEADING}\n\n{text.strip()}\n\n---\n\n{prompt}"
    return {
        "task_id": task.instance_id,
        "arm": arm,
        "title": f"csbench {cfg['run']} {arm} {task.instance_id[-8:]}",
        "model": cfg["model"],
        "source_url": task.repo_url,
        "source_revision": task.base_commit,
        "prompt": prompt,
    }


def parse_locations(text: str, repo: str, limit: int) -> list[tuple[str, int, int]]:
    """Locations from the last JSON block of the agent's final reply."""
    blocks = _JSON_BLOCK.findall(text or "")
    if not blocks:
        return []
    try:
        locs = json.loads(blocks[-1]).get("locations", [])
    except (json.JSONDecodeError, AttributeError):
        return []
    name = repo.split("/")[-1]
    out = []
    for loc in locs[:limit]:
        try:
            path = str(loc["file"])
            start = int(loc.get("start_line") or 1)
            end = int(loc.get("end_line") or start)
        except (KeyError, TypeError, ValueError):
            continue
        # strip an absolute checkout prefix such as /home/user/<repo>/
        if path.startswith("/") and f"/{name}/" in path:
            path = path.split(f"/{name}/", 1)[1]
        out.append((normalize_path(path), start, max(start, end)))
    return out


def score(task: Task, record: dict, limit: int) -> dict:
    locs = parse_locations(record.get("result_text", ""), task.repo, limit)
    hits = [ResolvedHit(f, s, e, ()) for f, s, e in locs]
    m = task_metrics(task.gold_lines, hits, budgets=())
    m.pop("tokens_returned")
    ok = record.get("status") == "ok"
    if not ok:
        m = {k: (None if v is None else 0.0) for k, v in m.items()}
    tokens = sum(record.get(k) or 0 for k in RECORD_FIELDS if k.endswith("_tokens"))
    return m | {
        "total_tokens": float(tokens) if ok else None,
        "output_tokens": float(record.get("output_tokens") or 0) if ok else None,
        "num_turns": float(record.get("num_turns") or 0) if ok else None,
        # None when the agent's CLI reports no cost, so it is not shown as free
        "cost_usd": float(record["cost_usd"]) if ok and record.get("cost_usd") is not None
        else None,
        "duration_s": float(record.get("duration_s") or 0) if ok else None,
        "n_locations": len(locs),
        "ok": ok,
    }


def ranges(nums: list[int]) -> str:
    """[1, 2, 3, 7] -> '1-3, 7'."""
    out: list[str] = []
    for n in nums:
        if out and out[-1].split("-")[-1] == str(n - 1):
            out[-1] = f"{out[-1].split('-')[0]}-{n}"
        else:
            out.append(str(n))
    return ", ".join(out)


def summarize(cfg: dict, root: Path, parquet: Path, out_dir: Path) -> str:
    """Score every saved session, write compact records and a summary table."""
    run_dir = root / ".cache" / "trackb" / cfg["run"]
    by_task = {t.instance_id: t for t in tasks(cfg, root, parquet)}
    scored: dict[str, dict[str, dict]] = {}
    raw: dict[str, dict[str, dict]] = {}
    records = []
    for arm in cfg["arms"]:
        for path in sorted((run_dir / arm).glob("*.json")):
            rec = json.loads(path.read_text())
            if rec["task_id"] not in by_task:
                continue
            s = score(by_task[rec["task_id"]], rec, cfg["max_locations"])
            scored.setdefault(arm, {})[rec["task_id"]] = s
            raw.setdefault(arm, {})[rec["task_id"]] = rec
            extra = {k: rec[k] for k in EXTRA_FIELDS if k in rec}
            records.append({k: rec.get(k) for k in RECORD_FIELDS if k != "result_text"} | extra | s)
    committed = out_dir / "records.jsonl.gz"
    if not records and committed.exists():
        # No session files (the cloud run's are gone): use the committed, already scored records.
        for line in gzip.decompress(committed.read_bytes()).decode().splitlines():
            rec = json.loads(line)
            if rec["task_id"] in by_task and rec["arm"] in cfg["arms"]:
                scored.setdefault(rec["arm"], {})[rec["task_id"]] = rec
                raw.setdefault(rec["arm"], {})[rec["task_id"]] = rec
                records.append(rec)
    arms =[a for a in cfg["arms"] if a in scored]
    common = sorted(set.intersection(*(set(scored[a]) for a in arms))) if arms else []
    lines = [
        f"# Track B: {cfg['run']}",
        "",
        f"Model `{cfg['model']}`; {len(common)} tasks with a finished session in every arm. "
        "Means with 95% bootstrap CIs (B = 1000, seed 42); cost over successful sessions. "
        "total_tokens counts input, output and cache read and write tokens as reported by the "
        "session; cost_usd is the session's own list-price cost. Tool used: sessions that ran "
        "the arm's tool at least once (where collected); Blocked: sessions with a call blocked "
        "by the permission check.",
        "",
        "## Sessions per arm",
        "",
        "| Arm | Records | OK | Cost USD | Missing task indices (0-based, sample order) |",
        "|---|---|---|---|---|",
    ]
    order = list(by_task)
    for arm in cfg["arms"]:
        recs = raw.get(arm, {})
        missing = ranges([i for i, t in enumerate(order) if t not in recs])
        cost = sum(r.get("cost_usd") or 0 for r in recs.values())
        ok = sum(r.get("status") == "ok" for r in recs.values())
        lines.append(
            f"| {arm} | {len(recs)}/{len(order)} | {ok} | {cost:.2f} | {missing or 'none'} |"
        )
    lines += [
        "",
        "## Results on tasks finished in every arm",
        "",
        "| Arm | Done | Tool used | Blocked | " + " | ".join(QUALITY + COST) + " |",
        "|" + "---|" * (4 + len(QUALITY) + len(COST)),
    ]
    for arm in arms:
        rows = [scored[arm][t] for t in common]
        cells = []
        for key in QUALITY + COST:
            vals = [r[key] for r in rows if r[key] is not None]
            if not vals:
                cells.append("n/a")
                continue
            mean, lo, hi = bootstrap_ci(np.array(vals))
            fmt = "{:.3f}" if key in QUALITY or key == "cost_usd" else "{:,.0f}"
            cells.append(f"{fmt.format(mean)} [{fmt.format(lo)}, {fmt.format(hi)}]")
        done = f"{sum(r['ok'] for r in rows)}/{len(rows)}"
        recs = [raw[arm][t] for t in common]
        known = [r for r in recs if r.get("tool_calls") is not None]
        used = f"{sum(r['tool_calls'] > 0 for r in known)}/{len(known)}" if known else "n/a"
        blocked = sum(1 for r in recs if r.get("permission_denials"))
        lines.append(f"| {arm} | {done} | {used} | {blocked} | " + " | ".join(cells) + " |")
    if "baseline" in arms and len(arms) > 1 and common:
        lines += [
            "",
            "Paired bootstrap against `baseline`:",
            "",
            "| Arm | Metric | Diff | 95% CI | p |",
            "|---|---|---|---|---|",
        ]
        for arm in arms:
            if arm == "baseline":
                continue
            for key in QUALITY + ["total_tokens", "cost_usd", "duration_s"]:
                a = [scored[arm][t][key] for t in common]
                b = [scored["baseline"][t][key] for t in common]
                if None in a or None in b:
                    continue
                p = paired_bootstrap(np.array(a, float), np.array(b, float))
                f = "{:+.4f}" if key == "cost_usd" else "{:+.3f}"
                lines.append(
                    f"| {arm} | {key} | {f.format(p['diff'])} | "
                    f"[{f.format(p['ci_low'])}, {f.format(p['ci_high'])}] | {p['p_value']:.3f} |"
                )
    text = "\n".join(lines) + "\n"
    out_dir.mkdir(parents=True, exist_ok=True)
    data = "".join(json.dumps(r, sort_keys=True) + "\n" for r in records).encode()
    (out_dir / "records.jsonl.gz").write_bytes(gzip.compress(data, compresslevel=9, mtime=0))
    (out_dir / "summary.md").write_text(text)
    return text
