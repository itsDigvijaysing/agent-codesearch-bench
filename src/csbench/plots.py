"""Plots for the README.

Per run: file recall@10 against tokens returned and against query latency (one point per
tool with 95% bootstrap CIs on both axes), and file recall@10 next to line recall at 8,000
tokens. Across runs (``write_overview``): the v1 sample against the hard split, and Track B
accuracy next to session cost. Every tool or arm is named by a label, so identity never
depends on color alone. Light and dark variants are written for the README's ``<picture>``
element. Colors follow the reference palette of the data-viz method used here: one fixed
color per tool under test (blue semble, orange graphify, aqua code-review-graph, validated as
a set against both surfaces) and gray for the baselines.
"""

from __future__ import annotations

from pathlib import Path

THEMES = {
    "light": {
        "surface": "#fcfcfb",
        "text": "#0b0b0b",
        "muted": "#52514e",
        "grid": "#e8e7e3",
        "baseline": "#8a8984",
        "tools": {"semble": "#2a78d6", "graphify": "#eb6834", "code-review-graph": "#1baf7a"},
    },
    "dark": {
        "surface": "#1a1a19",
        "text": "#f0efec",
        "muted": "#c3c2b7",
        "grid": "#2e2e2c",
        "baseline": "#8a8984",
        "tools": {"semble": "#3987e5", "graphify": "#d95926", "code-review-graph": "#199e70"},
    },
}
PLOTS = {
    "recall_vs_tokens": ("tokens_returned", "Tokens returned per query (log scale)"),
    "recall_vs_latency": ("query_s", "Query latency (log scale)"),
}


def fmt_tokens(v: float, _pos=None) -> str:
    return f"{v / 1000:g}K" if v >= 1000 else f"{v:g}"


def fmt_seconds(v: float, _pos=None) -> str:
    return f"{v:g} s" if v >= 1 else f"{v * 1000:g} ms"


Y = "file_recall@10"


def color(theme: dict, name: str) -> str:
    """One fixed color per tool under test in every chart; baselines and other names in gray.

    Track B arm names match the tool names, so "baseline" (the agent alone) is gray too.
    """
    return theme["tools"].get(name, theme["baseline"])


def _plot(rows: list[dict], x_key: str, x_label: str, title: str, theme: dict, path: Path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.4), dpi=150)
    fig.patch.set_facecolor(theme["surface"])
    ax.set_facecolor(theme["surface"])
    pts = [r for r in rows if r.get(f"{x_key}_mean") and r.get(f"{Y}_mean") is not None]
    for r in pts:
        x, y = r[f"{x_key}_mean"], r[f"{Y}_mean"]
        ax.errorbar(
            x,
            y,
            xerr=[[x - r[f"{x_key}_lo"]], [r[f"{x_key}_hi"] - x]],
            yerr=[[y - r[f"{Y}_lo"]], [r[f"{Y}_hi"] - y]],
            fmt="o",
            ms=7,
            color=color(theme, r["tool"]),
            ecolor=color(theme, r["tool"]),
            elinewidth=1.2,
            capsize=0,
            markeredgecolor=theme["surface"],
            markeredgewidth=1.5,
            zorder=3,
        )
        ax.annotate(
            r["tool"],
            (x, y),
            xytext=(7, 5),
            textcoords="offset points",
            fontsize=8.5,
            color=theme["text"],
            zorder=4,
        )
    from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

    ax.set_xscale("log")
    ax.xaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
    ax.xaxis.set_major_formatter(
        FuncFormatter(fmt_tokens if x_key == "tokens_returned" else fmt_seconds)
    )
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_ylim(0, 1)
    ax.set_xlabel(x_label, color=theme["muted"], fontsize=9)
    ax.set_ylabel("File recall@10", color=theme["muted"], fontsize=9)
    ax.set_title(title, color=theme["text"], fontsize=10.5, loc="left", pad=10)
    ax.grid(True, which="major", color=theme["grid"], linewidth=0.8, linestyle="-")
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(theme["grid"])
    ax.tick_params(colors=theme["muted"], labelsize=8, which="both")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=theme["surface"], metadata={"Software": None})
    plt.close(fig)


def write(rows: list[dict], n_tasks: int, out_dir: Path) -> list[Path]:
    paths = []
    for name, (x_key, x_label) in PLOTS.items():
        title = f"File recall@10 against {x_label.split(' (')[0].lower()}, {n_tasks} tasks"
        for mode, theme in THEMES.items():
            path = out_dir / f"{name}_{mode}.png"
            _plot(rows, x_key, x_label, title, theme, path)
            paths.append(path)
    for mode, theme in THEMES.items():
        path = out_dir / f"files_vs_lines_{mode}.png"
        _files_vs_lines(rows, n_tasks, theme, path)
        paths.append(path)
    return paths


# Runs compared by write_overview; it skips any whose committed results are missing.
OVERVIEW_RUNS = ("v1", "hard")
TRACKB_RUN = "trackb-haiku"
TRACKB_PANELS = (
    ("file_recall@10", "File recall@10", "{:.2f}"),
    ("duration_s", "Time per session", "{:.0f} s"),
    ("total_tokens", "Tokens per session", None),
)


def _pyplot():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _style(ax, theme: dict, grid_axis: str = "x") -> None:
    ax.set_facecolor(theme["surface"])
    ax.grid(True, axis=grid_axis, color=theme["grid"], linewidth=0.8, linestyle="-")
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(theme["grid"])
    ax.tick_params(colors=theme["muted"], labelsize=8, which="both", length=0)


def _save(fig, theme: dict, path: Path) -> None:
    import matplotlib.pyplot as plt

    fig.patch.set_facecolor(theme["surface"])
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=theme["surface"], metadata={"Software": None})
    plt.close(fig)


def _hbars(ax, labels, means, lows, highs, theme: dict, fmt, colors=None, missing="n/a") -> None:
    """Thin horizontal bars from zero with a CI whisker and the value past the whisker.

    Each bar takes its label's color (see ``color``); the label names it, so identity never
    rests on color alone.
    """
    span = max([h for h in highs if h is not None] or [1.0])
    colors = colors or [color(theme, label) for label in labels]
    for i, (m, lo, hi) in enumerate(zip(means, lows, highs, strict=True)):
        if m is None:
            ax.text(span * 0.01, i, missing, va="center", fontsize=8, color=theme["muted"])
            continue
        ax.barh(i, m, height=0.38, color=colors[i], zorder=2)
        end = m
        if lo is not None and hi is not None:
            ax.plot([lo, hi], [i, i], color=theme["muted"], linewidth=1.1, zorder=3)
            end = hi
        ax.text(end + span * 0.02, i, fmt(m), va="center", fontsize=8, color=theme["text"])
    ax.set_yticks(range(len(labels)), labels, color=theme["text"], fontsize=8.5)
    ax.set_ylim(len(labels) - 0.5, -0.5)


def _files_vs_lines(rows: list[dict], n_tasks: int, theme: dict, path: Path) -> None:
    plt = _pyplot()
    rows = sorted(rows, key=lambda r: -(r.get(f"{Y}_mean") or 0))
    labels = [r["tool"] for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(8, 0.42 * len(rows) + 1.5), dpi=150, sharey=True)
    panels = (
        (Y, "Needed files in the top 10 results"),
        ("line_recall@8000tok", "Needed lines within 8,000 tokens"),
    )
    for ax, (key, label) in zip(axes, panels, strict=True):
        _style(ax, theme)
        get = [r.get(f"{key}_{s}") for s in ("mean", "lo", "hi") for r in rows]
        n = len(rows)
        _hbars(ax, labels, get[:n], get[n : 2 * n], get[2 * n :], theme, "{:.2f}".format)
        ax.set_xlim(0, 1)
        ax.set_title(label, color=theme["text"], fontsize=9, loc="left")
    axes[1].tick_params(axis="y", length=0)
    fig.suptitle(
        f"Finding the files against finding the lines, {n_tasks} tasks (95% CIs)",
        color=theme["text"],
        fontsize=10.5,
        x=0.02,
        ha="left",
    )
    fig.tight_layout()
    _save(fig, theme, path)


def _v1_vs_hard(runs: dict[str, list[dict]], theme: dict, path: Path) -> None:
    plt = _pyplot()
    (a_name, a_rows), (b_name, b_rows) = runs.items()
    b_by = {r["tool"]: r for r in b_rows}
    rows = sorted((r for r in a_rows if r["tool"] in b_by), key=lambda r: -r[f"{Y}_mean"])
    fig, ax = plt.subplots(figsize=(7, 0.42 * len(rows) + 1.6), dpi=150)
    _style(ax, theme)
    for i, r in enumerate(rows):
        a, b = r[f"{Y}_mean"], b_by[r["tool"]][f"{Y}_mean"]
        c = color(theme, r["tool"])
        ax.plot([b, a], [i, i], color=theme["grid"], linewidth=2, zorder=2)
        ax.plot(b, i, "o", ms=8, mfc=theme["surface"], mec=c, mew=2, zorder=3)
        ax.plot(a, i, "o", ms=8, color=c, mec=theme["surface"], mew=1.5, zorder=3)
    ax.set_yticks(range(len(rows)), [r["tool"] for r in rows], color=theme["text"], fontsize=8.5)
    ax.set_ylim(len(rows) - 0.5, -0.5)
    ax.set_xlim(0, 1)
    ax.set_xlabel("File recall@10", color=theme["muted"], fontsize=9)
    n_a, n_b = int(a_rows[0]["n_tasks"]), int(b_rows[0]["n_tasks"])
    key = theme["muted"]
    handles = [
        plt.Line2D([], [], marker="o", ls="", ms=8, color=key, mec=theme["surface"]),
        plt.Line2D([], [], marker="o", ls="", ms=8, mfc=theme["surface"], mec=key, mew=2),
    ]
    ax.legend(
        handles,
        [f"{a_name}: {n_a} Python tasks", f"{b_name}: {n_b} tasks in large projects"],
        loc="lower right",
        frameon=False,
        fontsize=8,
        labelcolor=theme["text"],
    )
    ax.set_title(
        "File recall@10 on the v1 sample and on the hard split of large projects",
        color=theme["text"],
        fontsize=10.5,
        loc="left",
        pad=10,
    )
    fig.tight_layout()
    _save(fig, theme, path)


def _arm_label(arm: str) -> str:
    return "Agent alone" if arm == "baseline" else f"Agent + {arm}"


def _trackb(records: list[dict], theme: dict, path: Path) -> None:
    import numpy as np

    from csbench.metrics import bootstrap_ci

    plt = _pyplot()
    by: dict[str, dict[str, dict]] = {}
    for r in records:
        if r.get("ok", True):
            by.setdefault(r["arm"], {})[r["task_id"]] = r
    arms = list(by)
    common = sorted(set.intersection(*(set(v) for v in by.values())))
    fig, axes = plt.subplots(1, 3, figsize=(9, 0.5 * len(arms) + 1.5), dpi=150, sharey=True)
    for ax, (key, label, spec) in zip(axes, TRACKB_PANELS, strict=True):
        _style(ax, theme)
        stats = [bootstrap_ci(np.array([by[a][t][key] for t in common], float)) for a in arms]
        means, lows, highs = (list(x) for x in zip(*stats, strict=True))
        fmt = spec.format if spec else (lambda v: fmt_tokens(round(v, -3)))
        labels, colors = [_arm_label(a) for a in arms], [color(theme, a) for a in arms]
        _hbars(ax, labels, means, lows, highs, theme, fmt, colors)
        ax.set_xlim(0, 1 if key == Y else max(highs) * 1.3)
        if key == "total_tokens":
            from matplotlib.ticker import FuncFormatter

            ax.xaxis.set_major_formatter(FuncFormatter(fmt_tokens))
        ax.set_title(label, color=theme["text"], fontsize=9, loc="left")
    fig.suptitle(
        f"Track B: an agent with each tool, {len(common)} tasks finished in every arm (95% CIs)",
        color=theme["text"],
        fontsize=10.5,
        x=0.02,
        ha="left",
    )
    fig.tight_layout()
    _save(fig, theme, path)


def _read_summary(path: Path) -> list[dict]:
    import csv

    def num(v: str):
        try:
            return float(v)
        except ValueError:
            return v or None

    with path.open() as fh:
        return [{k: num(v) for k, v in row.items()} for row in csv.DictReader(fh)]


def write_overview(results: Path) -> list[Path]:
    """Cross-run plots from committed results, written to ``results/plots/``."""
    import gzip
    import json

    out, paths = results / "plots", []
    runs = {
        run: _read_summary(results / run / "summary.csv")
        for run in OVERVIEW_RUNS
        if (results / run / "summary.csv").exists()
    }
    records_path = results / TRACKB_RUN / "records.jsonl.gz"
    records = []
    if records_path.exists():
        with gzip.open(records_path, "rt") as fh:
            records = [json.loads(line) for line in fh]
    for mode, theme in THEMES.items():
        if len(runs) == 2:
            paths.append(out / f"v1_vs_hard_{mode}.png")
            _v1_vs_hard(runs, theme, paths[-1])
        if records:
            paths.append(out / f"trackb_{mode}.png")
            _trackb(records, theme, paths[-1])
    return paths
