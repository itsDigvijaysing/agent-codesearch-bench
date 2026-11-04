"""Command line: ``csbench {sample,run,report,all} --config configs/v1.yaml``."""

from __future__ import annotations

import argparse

from csbench import report, runner
from csbench.config import Config


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="csbench")
    ap.add_argument("command", choices=["sample", "run", "report", "all"])
    ap.add_argument("--config", default="configs/v1.yaml")
    ap.add_argument("--tools", nargs="+", help="subset of tools from the config")
    ap.add_argument("--limit", type=int, help="first N tasks of the sample")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--time-budget-min", type=float, help="stop starting tasks after N minutes")
    args = ap.parse_args(argv)
    cfg = Config.load(args.config)
    if args.command == "sample":
        print(runner.write_sample(cfg))
        return 0
    if args.command in ("run", "all"):
        runner.run(
            cfg,
            tools=args.tools,
            limit=args.limit,
            retry_failed=args.retry_failed,
            time_budget_s=args.time_budget_min * 60 if args.time_budget_min else None,
        )
    if args.command in ("report", "all"):
        print(report.write(cfg, args.tools))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
