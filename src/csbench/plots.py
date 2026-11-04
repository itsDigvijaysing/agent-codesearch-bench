"""Trade-off plots for the README: file recall@10 against tokens returned and query latency.

One point per tool with 95% bootstrap CIs on both axes. Every tool shares one color and is
named by a direct label, so identity never depends on color. Light and dark variants are
written for the README's ``<picture>`` element. Colors follow the reference palette of the
data-viz method used here (series-1 blue, validated against both surfaces).
"""

from __future__ import annotations

from pathlib import Path

THEMES = {
    "light": {
        "surface": "#fcfcfb",
        "text": "#0b0b0b",
        "muted": "#52514e",
        "grid": "#e8e7e3",
        "series": "#2a78d6",
    },
    "dark": {
        "surface": "#1a1a19",
        "text": "#f0efec",
        "muted": "#c3c2b7",
        "grid": "#2e2e2c",
        "series": "#3987e5",
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
            color=theme["series"],
            ecolor=theme["series"],
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
    return paths
