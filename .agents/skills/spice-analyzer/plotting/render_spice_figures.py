"""Render spice-analyzer figure PNGs/SVGs with dev-plot style (cross-platform).

Lives in the spice-analyzer skill: ``.agents/skills/spice-analyzer/plotting/``.

Uses sibling ``plot_style.py`` (vendored from the Cursor ``dev-plot`` skill).
Prefer SVG when matplotlib is available; always also write PNG for pdflatex.

Unix::

    python3 .agents/skills/spice-analyzer/plotting/render_spice_figures.py results/<run_id>
    bash .agents/skills/spice-analyzer/plotting/render_all.sh results/<run_id>

Windows (Python preferred; else PowerShell fallback)::

    python .agents/skills/spice-analyzer/plotting/render_spice_figures.py results/<run_id>
    powershell -File .agents/skills/spice-analyzer/plotting/render_all.ps1 -RunDir results/<run_id>
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Allow ``from plot_style import ...`` when invoked as a script from any cwd
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from plot_style import (
    BAR_COLOR,
    BAR_EDGE_COLOR,
    BAR_EDGE_WIDTH,
    DPI,
    FIGSIZE_COL,
    FIGSIZE_COL_WIDE,
    LABEL_SIZE,
    LEGEND_SIZE,
    LINEWIDTH_MAIN,
    LINEWIDTH_SECONDARY,
    MULTI_SERIES_COLORS,
    TICK_SIZE,
    TITLE_SIZE,
    apply_rcparams,
    apply_style,
    downsample_stride,
)

BACKENDS = ("cmos", "sky130", "ihp", "gf180")


def _load_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            try:
                rows.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
    if not rows:
        raise ValueError(f"no data in {path}")
    arr = np.asarray(rows, dtype=float)
    return arr[:, 0], arr[:, 1]


def _save(fig: plt.Figure, out_base: Path) -> None:
    out_base.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_base.with_suffix(".svg"), format="svg")
    fig.savefig(out_base.with_suffix(".png"), format="png", dpi=DPI)
    plt.close(fig)
    print(f"wrote {out_base}.png")


def _maybe(path: Path) -> bool:
    return path.is_file()


def plot_bode_mag(dat: Path, out_base: Path, title: str) -> None:
    f, y = _load_xy(dat)
    stride = downsample_stride(len(f))
    f, y = f[::stride], y[::stride]
    fig, ax = plt.subplots(figsize=FIGSIZE_COL_WIDE)
    ax.semilogx(f, y, color=MULTI_SERIES_COLORS[0], linewidth=LINEWIDTH_MAIN)
    ax.set_title(title, fontsize=TITLE_SIZE, fontweight="bold")
    ax.set_xlabel("Frequency (Hz)", fontsize=LABEL_SIZE)
    ax.set_ylabel("Gain (dB)", fontsize=LABEL_SIZE)
    apply_style(ax)
    _save(fig, out_base)


def plot_bode_phase(dat: Path, out_base: Path, title: str) -> None:
    f, y = _load_xy(dat)
    stride = downsample_stride(len(f))
    f, y = f[::stride], y[::stride]
    fig, ax = plt.subplots(figsize=FIGSIZE_COL_WIDE)
    ax.semilogx(f, y, color=MULTI_SERIES_COLORS[1], linewidth=LINEWIDTH_MAIN)
    ax.set_title(title, fontsize=TITLE_SIZE, fontweight="bold")
    ax.set_xlabel("Frequency (Hz)", fontsize=LABEL_SIZE)
    ax.set_ylabel("Phase (deg)", fontsize=LABEL_SIZE)
    apply_style(ax)
    _save(fig, out_base)


def plot_log_metric(dat: Path, out_base: Path, title: str, ylabel: str, color: str) -> None:
    f, y = _load_xy(dat)
    stride = downsample_stride(len(f))
    f, y = f[::stride], y[::stride]
    fig, ax = plt.subplots(figsize=FIGSIZE_COL_WIDE)
    ax.semilogx(f, y, color=color, linewidth=LINEWIDTH_MAIN)
    ax.set_title(title, fontsize=TITLE_SIZE, fontweight="bold")
    ax.set_xlabel("Frequency (Hz)", fontsize=LABEL_SIZE)
    ax.set_ylabel(ylabel, fontsize=LABEL_SIZE)
    apply_style(ax)
    _save(fig, out_base)


def plot_psrr_overlay(psrp: Path, psrn: Path, out_base: Path, title: str) -> None:
    f1, y1 = _load_xy(psrp)
    f2, y2 = _load_xy(psrn)
    s = downsample_stride(len(f1), combined=True)
    fig, ax = plt.subplots(figsize=FIGSIZE_COL_WIDE)
    ax.semilogx(
        f1[::s], y1[::s], color=MULTI_SERIES_COLORS[0],
        linewidth=LINEWIDTH_SECONDARY, label="PSRR+",
    )
    ax.semilogx(
        f2[::s], y2[::s], color=MULTI_SERIES_COLORS[1],
        linewidth=LINEWIDTH_SECONDARY, label="PSRR-",
    )
    ax.set_title(title, fontsize=TITLE_SIZE, fontweight="bold")
    ax.set_xlabel("Frequency (Hz)", fontsize=LABEL_SIZE)
    ax.set_ylabel("Gain (dB)", fontsize=LABEL_SIZE)
    ax.legend(fontsize=LEGEND_SIZE, loc="best", frameon=False)
    apply_style(ax)
    _save(fig, out_base)


def plot_bars(csv_path: Path, out_base: Path, title: str, xcol: str, ycols: list[str], ylabel: str) -> None:
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return
    ycol = next((c for c in ycols if c in rows[0]), None)
    if ycol is None:
        print(f"skip bars {csv_path}: no y column in {ycols}")
        return
    xs = [r[xcol] for r in rows]
    ys = []
    for r in rows:
        v = float(r[ycol])
        if ycol in ("gbw", "ugf") and v > 1e4:
            v = v / 1e6
        ys.append(v)
    fig, ax = plt.subplots(figsize=FIGSIZE_COL)
    ax.bar(xs, ys, color=BAR_COLOR, edgecolor=BAR_EDGE_COLOR, linewidth=BAR_EDGE_WIDTH)
    ax.set_title(title, fontsize=TITLE_SIZE, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=LABEL_SIZE)
    ax.tick_params(axis="x", rotation=25, labelsize=TICK_SIZE)
    apply_style(ax, grid_axis="y")
    _save(fig, out_base)


def plot_hist(csv_path: Path, out_base: Path, title: str, xlabel: str) -> None:
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return
    names = list(rows[0].keys())
    if "bin_center" in names and "count" in names:
        centers = [float(r["bin_center"]) for r in rows]
        counts = [float(r["count"]) for r in rows]
    else:
        val_col = next((n for n in names if n.lower() != "run"), names[0])
        vals = np.array([float(r[val_col]) for r in rows], dtype=float)
        if "ugf" in val_col.lower() or "gbw" in val_col.lower():
            if np.nanmax(vals) > 1e4:
                vals = vals / 1e6
        counts, edges = np.histogram(vals, bins=min(20, max(8, int(np.ceil(np.sqrt(len(vals)))))))
        centers = 0.5 * (edges[:-1] + edges[1:])
    if len(centers) > 1:
        width = 0.9 * (centers[1] - centers[0])
    else:
        width = 0.1
    fig, ax = plt.subplots(figsize=FIGSIZE_COL)
    ax.bar(
        centers, counts, width=width, color=BAR_COLOR,
        edgecolor=BAR_EDGE_COLOR, linewidth=BAR_EDGE_WIDTH, align="center",
    )
    ax.set_title(title, fontsize=TITLE_SIZE, fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=LABEL_SIZE)
    ax.set_ylabel("Count", fontsize=LABEL_SIZE)
    apply_style(ax, grid_axis="y")
    _save(fig, out_base)


def _psrr_paths(fig: Path) -> tuple[Path, Path] | None:
    pairs = [
        (fig / "psrr_p.dat", fig / "psrr_n.dat"),
        (fig / "psrrp.dat", fig / "psrrn.dat"),
    ]
    for a, b in pairs:
        if a.is_file() and b.is_file():
            return a, b
    return None


def render_backend(run_dir: Path, backend: str) -> None:
    fig = run_dir / backend / "figures"
    if not fig.is_dir():
        return
    label = backend
    if _maybe(fig / "bode_mag.dat"):
        plot_bode_mag(fig / "bode_mag.dat", fig / "bode_mag", f"{label} Bode magnitude")
    if _maybe(fig / "bode_phase.dat"):
        plot_bode_phase(fig / "bode_phase.dat", fig / "bode_phase", f"{label} Bode phase")
    if _maybe(fig / "cmrr.dat"):
        plot_log_metric(fig / "cmrr.dat", fig / "cmrr", f"{label} CMRR", "Gain (dB)", MULTI_SERIES_COLORS[0])
    psrr = _psrr_paths(fig)
    if psrr:
        plot_psrr_overlay(psrr[0], psrr[1], fig / "psrr", f"{label} PSRR+/PSRR-")
    if _maybe(fig / "noise.dat"):
        plot_log_metric(
            fig / "noise.dat", fig / "noise", f"{label} input-referred noise",
            "en (V/rtHz)", MULTI_SERIES_COLORS[2],
        )
    corners = fig / "corners.csv"
    if not corners.is_file():
        corners = run_dir / backend / "sim" / "corners.csv"
    if corners.is_file():
        # detect corner column
        with corners.open(newline="", encoding="utf-8") as fh:
            cols = list(csv.DictReader(fh).fieldnames or [])
        xcol = "corner" if "corner" in cols else cols[0]
        plot_bars(
            corners, fig / "corners_ugf", f"{label} corners - UGF", xcol,
            ["ugf_mhz", "gbw", "ugf"], "UGF (MHz)",
        )
        plot_bars(
            corners, fig / "corners_gain", f"{label} corners - DC gain", xcol,
            ["dcgain", "gain", "Adc_dB"], "Gain (dB)",
        )
    for name, xlab in (("mc_ugf_hist", "UGF (MHz)"), ("mc_pm_hist", "PM (deg)")):
        for cand in (fig / f"{name}.csv", run_dir / backend / "sim" / f"{name}.csv"):
            if cand.is_file():
                plot_hist(cand, fig / name, f"{label} {name}", xlab)
                break


def render_run(run_dir: Path) -> None:
    apply_rcparams()
    for be in BACKENDS:
        render_backend(run_dir, be)

    cross = run_dir / "figures_cross.csv"
    if cross.is_file():
        out = run_dir / "figures"
        out.mkdir(parents=True, exist_ok=True)
        specs = (
            ("cross_ugf", "Cross-backend UGF", ["ugf_mhz"], "UGF (MHz)"),
            ("cross_gain", "Cross-backend DC gain", ["dcgain"], "Gain (dB)"),
            ("cross_pm", "Cross-backend PM", ["pm_deg", "pm"], "PM (deg)"),
            ("cross_power", "Cross-backend power", ["power_mw", "power"], "P (mW)"),
        )
        for name, title, ycols, ylab in specs:
            plot_bars(cross, out / name, title, "backend", list(ycols), ylab)
            # also root copies for older report paths
            plot_bars(cross, run_dir / name, title, "backend", list(ycols), ylab)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", type=Path)
    args = ap.parse_args()
    render_run(args.run_dir.resolve())
    print(f"rendered figures under {args.run_dir}")


if __name__ == "__main__":
    main()
