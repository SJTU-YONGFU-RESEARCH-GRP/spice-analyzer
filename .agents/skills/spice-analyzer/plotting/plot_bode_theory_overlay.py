#!/usr/bin/env python3
"""Bode magnitude/phase: simulation vs hand-analysis TF overlay (cross-platform).

Lives in the spice-analyzer skill: ``.agents/skills/spice-analyzer/plotting/``.

Dev-plot palette: sim=#0033cc, hand=#cc0000

Hand TF (amplifier default)::

    A(s) = A0 (1+s/wz) / [(1+s/wp1)(1+s/wp2)(1+s/wp3)]

Poles/zeros typically come from final OP gm + caps (see hand_tf_params.txt).
Phase adds +180° when the TB AC-drives VINN (``vinn_drive=1``).

Usage (Unix / Windows with Python + matplotlib)::

    python3 .agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.py results/<run_id>
    python3 .agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.py results/<run_id> --backend sky130

Windows fallback without matplotlib: sibling ``plot_bode_theory_overlay.ps1``

Expects per backend:
  <backend>/sim/hand_tf_params.txt
  <backend>/figures/bode_mag.dat, bode_phase.dat
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from plot_style import (
    DPI,
    FIGSIZE_COL_WIDE,
    LABEL_SIZE,
    LEGEND_SIZE,
    LINEWIDTH_MAIN,
    LINEWIDTH_SECONDARY,
    MULTI_SERIES_COLORS,
    TITLE_SIZE,
    apply_rcparams,
    apply_style,
    downsample_stride,
)

BACKENDS = ("cmos", "sky130", "ihp", "gf180")


def _load_params(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _load_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
    rows: list[tuple[float, float]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            try:
                f, y = float(parts[0]), float(parts[1])
            except ValueError:
                continue
            if f > 0:
                rows.append((f, y))
    if len(rows) < 2:
        raise ValueError(f"need >=2 points in {path}")
    arr = np.asarray(rows, dtype=float)
    return arr[:, 0], arr[:, 1]


def _theory(
    f: np.ndarray,
    a0: float,
    fp1: float,
    fp2: float,
    fp3: float,
    fz: float,
    vinn_drive: bool,
) -> tuple[np.ndarray, np.ndarray]:
    def mag_fact(fx: float) -> np.ndarray:
        return np.sqrt(1.0 + (f / fx) ** 2)

    def arg_deg(fx: float) -> np.ndarray:
        return np.degrees(np.arctan(f / fx))

    mag_lin = a0 * mag_fact(fz) / (mag_fact(fp1) * mag_fact(fp2) * mag_fact(fp3))
    mag_db = 20.0 * np.log10(np.maximum(mag_lin, 1e-30))
    ph = arg_deg(fz) - arg_deg(fp1) - arg_deg(fp2) - arg_deg(fp3)
    if vinn_drive:
        ph = 180.0 + ph
    return mag_db, ph


def _save_xy(path: Path, f: np.ndarray, y: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="\n") as fh:
        for fi, yi in zip(f, y):
            fh.write(f"{fi:.10E}  {yi:.10E}\n")


def _save_fig(fig: plt.Figure, out_base: Path) -> None:
    out_base.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_base.with_suffix(".svg"), format="svg")
    fig.savefig(out_base.with_suffix(".png"), format="png", dpi=DPI)
    plt.close(fig)


def plot_overlay(
    f_sim: np.ndarray,
    y_sim: np.ndarray,
    f_thy: np.ndarray,
    y_thy: np.ndarray,
    out_base: Path,
    title: str,
    ylabel: str,
) -> None:
    s = downsample_stride(len(f_sim), combined=True)
    fig, ax = plt.subplots(figsize=FIGSIZE_COL_WIDE)
    ax.semilogx(
        f_sim[::s],
        y_sim[::s],
        color=MULTI_SERIES_COLORS[0],
        linewidth=LINEWIDTH_MAIN,
        label="Sim",
    )
    ax.semilogx(
        f_thy[::s],
        y_thy[::s],
        color=MULTI_SERIES_COLORS[1],
        linewidth=LINEWIDTH_SECONDARY,
        label="Hand TF",
    )
    ax.set_title(title, fontsize=TITLE_SIZE, fontweight="bold")
    ax.set_xlabel("Frequency (Hz)", fontsize=LABEL_SIZE)
    ax.set_ylabel(ylabel, fontsize=LABEL_SIZE)
    ax.legend(fontsize=LEGEND_SIZE, loc="best", frameon=False)
    apply_style(ax)
    _save_fig(fig, out_base)


def process_backend(run_dir: Path, backend: str) -> None:
    fig = run_dir / backend / "figures"
    sim_mag = fig / "bode_mag.dat"
    sim_ph = fig / "bode_phase.dat"
    params = _load_params(run_dir / backend / "sim" / "hand_tf_params.txt")
    if not sim_mag.is_file():
        print(f"skip {backend}: missing bode_mag.dat")
        return
    need = ("A0_lin", "fp1_Hz", "fp2_Hz", "fp3_Hz", "fz_Hz")
    if any(k not in params for k in need):
        print(f"skip {backend}: missing hand_tf_params.txt keys {need}")
        return

    a0 = float(params["A0_lin"])
    fp1 = float(params["fp1_Hz"])
    fp2 = float(params["fp2_Hz"])
    fp3 = float(params["fp3_Hz"])
    fz = float(params["fz_Hz"])
    vinn = params.get("vinn_drive", "1") != "0"

    f_sim, y_mag_sim = _load_xy(sim_mag)
    try:
        f_ph, y_ph_sim = _load_xy(sim_ph)
    except ValueError:
        f_ph, y_ph_sim = f_sim, np.full_like(f_sim, np.nan)

    mag_thy, ph_thy = _theory(f_sim, a0, fp1, fp2, fp3, fz, vinn)
    # Phase theory on phase-file frequency grid if different
    if not np.allclose(f_ph, f_sim):
        _, ph_thy = _theory(f_ph, a0, fp1, fp2, fp3, fz, vinn)

    _save_xy(fig / "bode_mag_theory.dat", f_sim, mag_thy)
    _save_xy(fig / "bode_phase_theory.dat", f_ph, ph_thy)

    plot_overlay(
        f_sim,
        y_mag_sim,
        f_sim,
        mag_thy,
        fig / "bode_mag_overlay",
        f"{backend} Bode mag: sim vs hand",
        "Gain (dB)",
    )
    if np.isfinite(y_ph_sim).any():
        plot_overlay(
            f_ph,
            y_ph_sim,
            f_ph,
            ph_thy,
            fig / "bode_phase_overlay",
            f"{backend} Bode phase: sim vs hand",
            "Phase (deg)",
        )
    print(f"wrote {backend} Bode overlays")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", type=Path, help="results/<run_id>")
    ap.add_argument(
        "--backend",
        default="",
        help="single backend (default: all present among cmos/sky130/ihp/gf180)",
    )
    args = ap.parse_args()
    run_dir = args.run_dir.resolve()
    apply_rcparams()

    if args.backend:
        backends = [args.backend]
    else:
        backends = [b for b in BACKENDS if (run_dir / b / "figures" / "bode_mag.dat").is_file()]

    if not backends:
        raise SystemExit(f"no backends with bode_mag.dat under {run_dir}")

    for be in backends:
        process_backend(run_dir, be)
    print(f"done backends: {', '.join(backends)}")


if __name__ == "__main__":
    main()
