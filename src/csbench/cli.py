"""Command line: ``csbench {sample,lock,upgrade,run,report,all} --config configs/v1.yaml``.

Your own project: ``csbench try PATH`` mines tasks from the repository's git history and
ranks the tools on them (see ``tryrepo.py``).

Track B: ``csbench trackb-requests --arm ARM`` prints one session request per line (JSON);
``csbench trackb-report`` scores the saved sessions.

Exit codes: 0 done; 3 a run stopped at its time budget with pairs left (run it again);
4 a tool upgrade needs a maintainer to review a changed default.
"""

from __future__ import annotations

import argparse
import json
import sys

from csbench import report, runner
from csbench.config import Config


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="csbench")
    ap.add_argument(
        "command",
        choices=[
            "sample",
            "lock",
            "upgrade",
            "run",
            "report",
            "all",
            "try",
            "trackb-requests",
            "trackb-report",
        ],
    )
    ap.add_argument("path", nargs="?", help="repository to benchmark (try)")
    ap.add_argument("--config", default="configs/v1.yaml")
    ap.add_argument("--commits", type=int, default=20, help="tasks to mine (try)")
    ap.add_argument("--out", help="output directory (try; default ./csbench-try-<name>)")
    ap.add_argument("--tools", nargs="+", help="subset of tools from the config")
    ap.add_argument("--limit", type=int, help="first N tasks of the sample")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--time-budget-min", type=float, help="stop starting tasks after N minutes")
    ap.add_argument(
        "--fresh",
        action="store_true",
        help="ignore records committed in results/ and recompute every number",
    )
    ap.add_argument("--trackb-config", default="configs/trackb.yaml")
    ap.add_argument("--arm", help="Track B arm for trackb-requests")
    args = ap.parse_args(argv)
    budget = args.time_budget_min * 60 if args.time_budget_min else None
    if args.command == "try":
        from pathlib import Path

        from csbench import tryrepo
        from csbench.config import project_root

        repo = Path(args.path or ".").resolve()
        out = Path(args.out or f"csbench-try-{repo.name}")
        result, complete = tryrepo.run(project_root(), repo, out, args.commits, args.tools, budget)
        if not complete:
            return 3
        print((result / "summary.md").read_text())
        return 0
    cfg = Config.load(args.config)
    if args.command == "sample":
        print(runner.write_sample(cfg))
        return 0
    if args.command.startswith("trackb"):
        from csbench import trackb

        tcfg, root = trackb.load_config(args.trackb_config)
        parquet = runner.dataset_path(cfg)
        if args.command == "trackb-requests":
            for task in trackb.tasks(tcfg, root, parquet):
                print(json.dumps(trackb.session_request(tcfg, root, task, args.arm)))
        else:
            print(trackb.summarize(tcfg, root, parquet, cfg.path("results") / tcfg["run"]))
        return 0
    if args.command == "lock":
        for spec in cfg.tools(args.tools):
            if spec.env:
                print(runner.lock_env(cfg, spec))
        return 0
    if args.command == "upgrade":
        from csbench.upgrade import NeedsReview, upgrade

        try:
            for tool, old, new in upgrade(cfg, args.tools):
                print(f"{tool} {old} {new}")
        except NeedsReview as exc:
            print(f"needs review: {exc}", file=sys.stderr)
            return 4
        return 0
    if args.command in ("run", "all"):
        _, complete = runner.run(
            cfg,
            tools=args.tools,
            limit=args.limit,
            retry_failed=args.retry_failed,
            time_budget_s=budget,
            use_committed=not args.fresh,
        )
        if not complete:
            return 3
    if args.command in ("report", "all"):
        print(report.write(cfg, args.tools, use_committed=not args.fresh))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
