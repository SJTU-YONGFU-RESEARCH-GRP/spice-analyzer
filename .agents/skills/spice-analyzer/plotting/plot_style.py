"""Canonical matplotlib style for spice-analyzer report figures.

Sized for **LaTeX column embeds** (``FIGSIZE_COL*``). Do not reuse the old
dev-plot dashboard sizes (title 17 / line 7 on an 11x5 in figure) on these
canvases -- that made titles dominate the axes and look inconsistent in PDF.

Wide-dashboard aliases remain for rare non-report plots only.
"""

from __future__ import annotations

import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Column embed (default for all spice-analyzer report PNGs)
# ---------------------------------------------------------------------------
FIGSIZE_COL = (4.5, 2.8)
FIGSIZE_COL_WIDE = (4.5, 3.0)
DPI = 200

TITLE_SIZE = 10
LABEL_SIZE = 9
TICK_SIZE = 8
LEGEND_SIZE = 8

LINEWIDTH_MAIN = 2.2
LINEWIDTH_SECONDARY = 1.8
GRID_ALPHA = 0.35
GRID_LINEWIDTH = 0.8
SPINE_WIDTH = 1.2

BAR_COLOR = "#0033cc"  # close to MATLAB [0 0.2 1]
BAR_EDGE_COLOR = "#002080"
BAR_EDGE_WIDTH = 0.8

LINE_COLORS = {
    "energy": "#0033cc",
    "dnl": "#0033cc",
    "inl": "#cc0000",
    "sndr": "#0033cc",
    "sfdr": "#cc0000",
    "thd": "#7f3fbf",
    "enob": "#e67300",
}
MULTI_SERIES_COLORS = ("#0033cc", "#cc0000", "#7f3fbf")
PURPLE_CYCLE = ("#7f3fbf", "#9b59b6", "#6a1b9a", "#4a148c")
PROFILE_COLORS = {
    "baseline": "#0033cc",
    "variation_mc_mean": "#cc0000",
    "all_variation_parasitic": "#006400",
}
PROFILE_MARKERS = {
    "baseline": "^",
    "variation_mc_mean": "o",
    "all_variation_parasitic": "X",
}
PARASITIC_MARKERS = ("s", "d", "v", "P")

# ---------------------------------------------------------------------------
# Wide dashboard (optional; not used by report renderers)
# ---------------------------------------------------------------------------
FIGSIZE = (11, 5)
TITLE_SIZE_DASHBOARD = 17
LABEL_SIZE_DASHBOARD = 13
TICK_SIZE_DASHBOARD = 10
LINEWIDTH_MAIN_DASHBOARD = 7.0
LINEWIDTH_SECONDARY_DASHBOARD = 5.0


def apply_rcparams() -> None:
    """Set global typography once per process (column-embed defaults)."""
    plt.rcParams["font.family"] = "sans-serif"
    # DejaVu first: has a real Bold face on typical Linux/WSL installs.
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Liberation Sans", "Arial", "Helvetica"]
    # Keep default weight normal; apply bold only via fontweight= on titles/labels
    # so missing Bold faces do not spam findfont and fall back inconsistently.
    plt.rcParams["font.weight"] = "normal"
    plt.rcParams["axes.labelweight"] = "bold"
    plt.rcParams["axes.titleweight"] = "bold"
    plt.rcParams["axes.titlesize"] = TITLE_SIZE
    plt.rcParams["axes.labelsize"] = LABEL_SIZE
    plt.rcParams["xtick.labelsize"] = TICK_SIZE
    plt.rcParams["ytick.labelsize"] = TICK_SIZE
    plt.rcParams["legend.fontsize"] = LEGEND_SIZE
    plt.rcParams["lines.linewidth"] = LINEWIDTH_MAIN
    plt.rcParams["figure.dpi"] = DPI
    plt.rcParams["savefig.dpi"] = DPI
    plt.rcParams["savefig.bbox"] = "tight"
    plt.rcParams["savefig.pad_inches"] = 0.08


def apply_style(ax: plt.Axes, *, grid_axis: str | None = None) -> None:
    """Apply consistent axis styling to one axes."""
    if grid_axis is None:
        ax.grid(alpha=GRID_ALPHA, linewidth=GRID_LINEWIDTH)
    else:
        ax.grid(axis=grid_axis, alpha=GRID_ALPHA, linewidth=GRID_LINEWIDTH)
    ax.tick_params(axis="both", labelsize=TICK_SIZE)
    for spine in ax.spines.values():
        spine.set_linewidth(SPINE_WIDTH)
    ax.spines["top"].set_visible(True)
    ax.spines["right"].set_visible(True)


def downsample_stride(length: int, *, combined: bool = False) -> int:
    """Stride for long series before plotting."""
    divisor = 256 if combined else 512
    return max(length // divisor, 1)
