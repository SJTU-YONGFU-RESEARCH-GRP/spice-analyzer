#!/usr/bin/env python3
"""Characterize cmos.lib devices with ngspice; write plots under models/plots/."""

from __future__ import annotations

import argparse
import os
import random
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
LIB = MODELS / "cmos.lib"
PLOTS = MODELS / "plots"
WORK = MODELS / "char" / "work"
MC_DIR = MODELS / "char" / "mc_results"
NGSPICE = ROOT / "tools" / "Spice64" / "bin" / "ngspice_con.exe"

MOS_N = ["nmos_rvt", "nmos_nat", "nmos_hvt", "nmos_tox"]
MOS_P = ["pmos_rvt", "pmos_hvt", "pmos_tox"]
MOS_ALL = MOS_N + MOS_P
BJTS = ["npn_l1", "pnp_l1"]

MC_RUNS = 10_000
MC_TRACE_PLOT = 80
MC_WORKERS = max(1, min(16, (os.cpu_count() or 4)))
SEED = 42

_LIB_TEXT: str | None = None


def ensure_ngspice() -> Path:
    if NGSPICE.is_file():
        return NGSPICE
    found = shutil.which("ngspice_con") or shutil.which("ngspice")
    if found:
        return Path(found)
    sys.exit(
        f"ngspice not found at {NGSPICE}. "
        "Extract ngspice Spice64 under tools/ or put ngspice on PATH."
    )


def run_ngspice(deck: Path, cwd: Path) -> None:
    exe = ensure_ngspice()
    log = cwd / (deck.stem + ".log")
    cmd = [str(exe), "-b", "-a", "-o", str(log), str(deck.name)]
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        msg = log.read_text(encoding="utf-8", errors="replace")[-2000:] if log.exists() else r.stderr
        raise RuntimeError(f"ngspice failed on {deck} (exit {r.returncode})\n{msg}")


def read_wrdata(path: Path) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = [], []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("*") or line.startswith("#"):
            continue
        parts = line.replace(",", " ").split()
        if len(parts) < 2:
            continue
        try:
            xs.append(float(parts[0]))
            ys.append(float(parts[1]))
        except ValueError:
            continue
    if not xs:
        raise RuntimeError(f"no data in {path}")
    return np.asarray(xs), np.asarray(ys)


def write_deck(path: Path, body: str) -> None:
    path.write_text(body.strip() + "\n", encoding="utf-8", newline="\n")


def expand_lib_inline() -> str:
    global _LIB_TEXT
    if _LIB_TEXT is None:
        _LIB_TEXT = LIB.read_text(encoding="utf-8")
    return _LIB_TEXT


def mos_idvg_deck(model: str, out_dat: str, temp: float = 27.0, extra_params: str = "") -> str:
    nmos = model.startswith("nmos")
    vdd = 3.3 if "tox" in model else 1.8
    if nmos:
        circ = f"""
M1 d g 0 0 {model} W=1u L=0.18u
Vds d 0 {vdd}
Vgs g 0 0
.dc Vgs 0 {vdd} 0.01
"""
        cur = "-i(Vds)"
    else:
        circ = f"""
M1 d g s s {model} W=2u L=0.18u
Vs s 0 {vdd}
Vds d 0 0
Vgs g 0 {vdd}
.dc Vgs {vdd} 0 -0.01
"""
        cur = "i(Vds)"
    return f"""
* Id-Vgs {model} T={temp}
{expand_lib_inline()}
{extra_params}
.temp {temp}
{circ}
.control
set filetype=ascii
run
wrdata {out_dat} {cur}
.endc
.end
"""


def mos_idvd_deck(model: str, out_dat: str, temp: float = 27.0) -> str:
    vdd = 3.3 if "tox" in model else 1.8
    if model.startswith("nmos"):
        return f"""
* Id-Vds {model}
{expand_lib_inline()}
.temp {temp}
M1 d g 0 0 {model} W=1u L=0.18u
Vds d 0 0
Vgs g 0 0.6
.control
set filetype=ascii
foreach vgs 0.6 0.9 1.2 1.5 1.8
  destroy all
  alter Vgs $vgs
  dc Vds 0 {vdd} 0.02
  wrdata {out_dat}_$vgs -i(Vds)
end
.endc
.end
"""
    return f"""
* Id-Vds {model} PMOS
{expand_lib_inline()}
.temp {temp}
M1 d g s s {model} W=2u L=0.18u
Vs s 0 {vdd}
Vds d 0 {vdd}
Vgs g 0 {vdd}
.control
set filetype=ascii
foreach vsg 0.6 0.9 1.2 1.5 1.8
  destroy all
  let vg = {vdd} - $vsg
  alter Vgs $&vg
  dc Vds {vdd} 0 -0.02
  wrdata {out_dat}_$vsg i(Vds)
end
.endc
.end
"""


def bjt_icvbe_deck(model: str, out_dat: str, temp: float = 27.0, extra_params: str = "") -> str:
    npn = model.startswith("npn")
    if npn:
        circ = f"""
Q1 c b 0 {model}
Vce c 0 2
Vbe b 0 0
.dc Vbe 0.4 0.9 0.002
"""
        cur = "-i(Vce)"
    else:
        circ = f"""
Q1 c b e {model}
Ve e 0 2
Vc c 0 0
Vb b 0 2
.dc Vb 2 1.1 -0.002
"""
        cur = "i(Vc)"
    return f"""
* Ic-Vbe {model} T={temp}
{expand_lib_inline()}
{extra_params}
.temp {temp}
{circ}
.control
set filetype=ascii
run
wrdata {out_dat} {cur}
.endc
.end
"""


def style_axes(ax, xlabel: str, ylabel: str, title: str) -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.35)
    ax.legend(fontsize=8)


def find_data(work: Path, stem: str) -> Path:
    for cand in (work / f"{stem}.dat", work / stem):
        if cand.is_file():
            return cand
    cands = [
        p
        for p in work.glob(f"{stem}*")
        if p.is_file() and p.suffix.lower() not in {".log", ".sp", ".cir"}
    ]
    if not cands:
        raise FileNotFoundError(f"no wrdata for {stem} in {work}")
    return cands[0]


def plot_mos_idvg(work: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for model in MOS_N:
        deck = work / f"idvg_{model}.sp"
        dat = f"idvg_{model}.dat"
        write_deck(deck, mos_idvg_deck(model, dat))
        run_ngspice(deck, work)
        x, y = read_wrdata(work / dat)
        axes[0].plot(x, y * 1e6, label=model)
    style_axes(axes[0], r"$V_{GS}$ (V)", r"$I_D$ (µA)", "NMOS $I_D$–$V_{GS}$ @ $V_{DS}=V_{DD}$, 27 °C")

    for model in MOS_P:
        deck = work / f"idvg_{model}.sp"
        dat = f"idvg_{model}.dat"
        write_deck(deck, mos_idvg_deck(model, dat))
        run_ngspice(deck, work)
        x, y = read_wrdata(work / dat)
        vdd = 3.3 if "tox" in model else 1.8
        axes[1].plot(vdd - x, np.abs(y) * 1e6, label=model)
    style_axes(axes[1], r"$V_{SG}$ (V)", r"$|I_D|$ (µA)", "PMOS $|I_D|$–$V_{SG}$ @ $|V_{SD}|=V_{DD}$, 27 °C")

    out = PLOTS / "mos_id_vgs.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def plot_mos_idvd(work: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for ax, model, title in [
        (axes[0], "nmos_rvt", r"NMOS RVT $I_D$–$V_{DS}$ family"),
        (axes[1], "pmos_rvt", r"PMOS RVT $|I_D|$–$|V_{SD}|$ family"),
    ]:
        deck = work / f"idvd_{model}.sp"
        write_deck(deck, mos_idvd_deck(model, f"idvd_{model}"))
        run_ngspice(deck, work)
        vdd = 1.8
        for vgs in [0.6, 0.9, 1.2, 1.5, 1.8]:
            path = find_data(work, f"idvd_{model}_{vgs:g}")
            x, y = read_wrdata(path)
            if model.startswith("nmos"):
                ax.plot(x, y * 1e6, label=rf"$V_{{GS}}$={vgs:g}")
            else:
                ax.plot(vdd - x, np.abs(y) * 1e6, label=rf"$V_{{SG}}$={vgs:g}")
        xlab = r"$V_{DS}$ (V)" if model.startswith("nmos") else r"$|V_{SD}|$ (V)"
        style_axes(ax, xlab, r"$|I_D|$ (µA)", title + ", 27 °C")
    out = PLOTS / "mos_id_vds.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def plot_mos_temp(work: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    temps = [-40, 27, 125]
    for ax, model in [(axes[0], "nmos_rvt"), (axes[1], "pmos_rvt")]:
        for t in temps:
            deck = work / f"idvg_temp_{model}_{t}.sp"
            dat = f"idvg_temp_{model}_{t}.dat"
            write_deck(deck, mos_idvg_deck(model, dat, temp=t))
            run_ngspice(deck, work)
            x, y = read_wrdata(work / dat)
            if model.startswith("nmos"):
                ax.plot(x, y * 1e6, label=f"{t} °C")
            else:
                ax.plot(1.8 - x, np.abs(y) * 1e6, label=f"{t} °C")
        xlab = r"$V_{GS}$ (V)" if model.startswith("nmos") else r"$V_{SG}$ (V)"
        style_axes(ax, xlab, r"$|I_D|$ (µA)", f"{model} $I_D$–$V_{{GS}}$ vs temperature")
    out = PLOTS / "mos_id_vgs_temp.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def plot_bjt_icvbe(work: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for ax, model in [(axes[0], "npn_l1"), (axes[1], "pnp_l1")]:
        deck = work / f"icvbe_{model}.sp"
        dat = f"icvbe_{model}.dat"
        write_deck(deck, bjt_icvbe_deck(model, dat))
        run_ngspice(deck, work)
        x, y = read_wrdata(work / dat)
        if model.startswith("npn"):
            ax.semilogy(x, np.clip(np.abs(y), 1e-18, None), label=model)
            style_axes(ax, r"$V_{BE}$ (V)", r"$I_C$ (A)", "NPN $I_C$–$V_{BE}$ (Gummel), 27 °C")
        else:
            ax.semilogy(2.0 - x, np.clip(np.abs(y), 1e-18, None), label=model)
            style_axes(ax, r"$V_{EB}$ (V)", r"$|I_C|$ (A)", "PNP $|I_C|$–$V_{EB}$ (Gummel), 27 °C")
    out = PLOTS / "bjt_ic_vbe.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def plot_bjt_temp(work: Path) -> Path:
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    for t in [-40, 27, 125]:
        deck = work / f"icvbe_temp_npn_{t}.sp"
        dat = f"icvbe_temp_npn_{t}.dat"
        write_deck(deck, bjt_icvbe_deck("npn_l1", dat, temp=t))
        run_ngspice(deck, work)
        x, y = read_wrdata(work / dat)
        ax.semilogy(x, np.clip(np.abs(y), 1e-18, None), label=f"{t} °C")
    style_axes(ax, r"$V_{BE}$ (V)", r"$I_C$ (A)", r"NPN $I_C$–$V_{BE}$ vs temperature")
    out = PLOTS / "bjt_ic_vbe_temp.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def mc_extra_from_samples(*, nmos: bool, bjt: bool, u_a: float, u_b: float) -> str:
    lines = [".param mc=1"]
    if bjt:
        if nmos:
            lines += [f".param u_is_n={u_a:.8f}", f".param u_bf_n={u_b:.8f}"]
        else:
            lines += [f".param u_is_p={u_a:.8f}", f".param u_bf_p={u_b:.8f}"]
    else:
        if nmos:
            lines += [f".param u_vto_n={u_a:.8f}", f".param u_kp_n={u_b:.8f}"]
        else:
            lines += [f".param u_vto_p={u_a:.8f}", f".param u_kp_p={u_b:.8f}"]
    return "\n".join(lines)


def _normalize_curve(model: str, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return plot x and |I| (A)."""
    if model.startswith("nmos") or model.startswith("npn"):
        return x, np.abs(y)
    vdd = 3.3 if "tox" in model else (2.0 if model.startswith("pnp") else 1.8)
    if model.startswith("pnp"):
        return vdd - x, np.abs(y)
    return vdd - x, np.abs(y)


def _mc_one_trial(args: tuple) -> tuple[int, np.ndarray, np.ndarray]:
    """Worker: one ngspice MC trial. args=(kind, model, i, u_a, u_b, work_root)."""
    kind, model, i, u_a, u_b, work_root = args
    work_root = Path(work_root)
    slot = work_root / f"t{os.getpid()}_{i}"
    slot.mkdir(parents=True, exist_ok=True)
    try:
        stem = f"{kind}_{model}_{i}"
        dat = f"{stem}.dat"
        extra = mc_extra_from_samples(
            nmos=model.startswith(("nmos", "npn")),
            bjt=(kind == "bjt"),
            u_a=u_a,
            u_b=u_b,
        )
        if kind == "mos":
            body = mos_idvg_deck(model, dat, extra_params=extra)
        else:
            body = bjt_icvbe_deck(model, dat, extra_params=extra)
        deck = slot / f"{stem}.sp"
        write_deck(deck, body)
        run_ngspice(deck, slot)
        path = find_data(slot, stem)
        x, y = read_wrdata(path)
        return i, x, y
    finally:
        shutil.rmtree(slot, ignore_errors=True)


def run_spice_mc(
    *,
    kind: str,
    model: str,
    n: int,
    seed: int,
    work_root: Path,
    workers: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Full ngspice LOT MC. Returns x, y_nom, y_mc[n, npts] (plot units: A)."""
    work_root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    u_a = rng.normal(0.0, 1.0, size=n)
    u_b = rng.normal(0.0, 1.0, size=n)

    # nominal
    stem = f"{kind}_{model}_nom"
    if kind == "mos":
        body = mos_idvg_deck(model, f"{stem}.dat", extra_params=".param mc=0")
    else:
        body = bjt_icvbe_deck(model, f"{stem}.dat", extra_params=".param mc=0")
    deck = work_root / f"{stem}.sp"
    write_deck(deck, body)
    run_ngspice(deck, work_root)
    x0, y0 = read_wrdata(find_data(work_root, stem))
    x_nom, y_nom = _normalize_curve(model, x0, y0)

    tasks = [
        (kind, model, i, float(u_a[i]), float(u_b[i]), str(work_root))
        for i in range(n)
    ]
    ys = [None] * n
    t0 = time.perf_counter()
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_mc_one_trial, t) for t in tasks]
        for fut in as_completed(futs):
            i, x, y = fut.result()
            xx, yy = _normalize_curve(model, x, y)
            if xx.shape != x_nom.shape or not np.allclose(xx, x_nom, rtol=0, atol=1e-9):
                # resample onto nominal x if needed
                yy = np.interp(x_nom, xx[::-1] if xx[0] > xx[-1] else xx,
                               yy[::-1] if xx[0] > xx[-1] else yy)
            ys[i] = yy
            done += 1
            if done % 500 == 0 or done == n:
                dt = time.perf_counter() - t0
                rate = done / dt if dt > 0 else 0
                eta = (n - done) / rate if rate > 0 else 0
                print(
                    f"  {model}: {done}/{n}  {rate:.1f}/s  ETA {eta/60:.1f} min",
                    flush=True,
                )
    y_mc = np.vstack(ys)
    return x_nom, y_nom, y_mc


def plot_mc_band(ax, x, nom, mc, *, color: str, logy: bool = False) -> None:
    p5, p50, p95 = np.percentile(mc, [5, 50, 95], axis=0)
    if logy:
        ax.set_yscale("log")
        floor = 1e-18
        ax.fill_between(x, np.clip(p5, floor, None), np.clip(p95, floor, None),
                         color=color, alpha=0.25, linewidth=0, label="p5–p95")
        ax.plot(x, np.clip(p50, floor, None), color=color, alpha=0.8, lw=1.2, label="p50")
        idx = np.linspace(0, mc.shape[0] - 1, num=min(MC_TRACE_PLOT, mc.shape[0]), dtype=int)
        for i in idx:
            ax.plot(x, np.clip(mc[i], floor, None), color=color, alpha=0.03, lw=0.5)
        ax.plot(x, np.clip(nom, floor, None), color="k", lw=2.0, label="nominal")
    else:
        ax.fill_between(x, p5, p95, color=color, alpha=0.25, linewidth=0, label="p5–p95")
        ax.plot(x, p50, color=color, alpha=0.8, lw=1.2, label="p50")
        idx = np.linspace(0, mc.shape[0] - 1, num=min(MC_TRACE_PLOT, mc.shape[0]), dtype=int)
        for i in idx:
            ax.plot(x, mc[i], color=color, alpha=0.03, lw=0.5)
        ax.plot(x, nom, color="k", lw=2.0, label="nominal")


def plot_mos_mc(work: Path, n: int = MC_RUNS, workers: int = MC_WORKERS) -> list[Path]:
    """Full ngspice 10k LOT MC for every MOSFET flavor."""
    MC_DIR.mkdir(parents=True, exist_ok=True)
    outs: list[Path] = []
    # overview figure (rvt only) kept for README top link
    overview = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    fig_ov, axes_ov = overview

    for mi, model in enumerate(MOS_ALL):
        print(f"MOS MC ngspice n={n:,} workers={workers}: {model}", flush=True)
        x, nom, mc = run_spice_mc(
            kind="mos",
            model=model,
            n=n,
            seed=SEED + mi * 1009,
            work_root=work / "mc",
            workers=workers,
        )
        np.savez_compressed(
            MC_DIR / f"{model}_idvg_mc.npz",
            x=x,
            nominal=nom,
            mc=mc,
            n=n,
            engine="ngspice",
        )
        # per-device plot in µA
        fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
        plot_mc_band(ax, x, nom * 1e6, mc * 1e6, color="C0" if model.startswith("n") else "C1")
        xlab = r"$V_{GS}$ (V)" if model.startswith("nmos") else r"$V_{SG}$ (V)"
        style_axes(ax, xlab, r"$|I_D|$ (µA)", f"{model} LOT MC ngspice (n={n:,})")
        out = PLOTS / f"mc_{model}_id_vgs.png"
        fig.savefig(out, dpi=140)
        plt.close(fig)
        outs.append(out)

        if model == "nmos_rvt":
            plot_mc_band(axes_ov[0], x, nom * 1e6, mc * 1e6, color="C0")
            style_axes(axes_ov[0], r"$V_{GS}$ (V)", r"$|I_D|$ (µA)", f"{model} LOT MC ngspice (n={n:,})")
        if model == "pmos_rvt":
            plot_mc_band(axes_ov[1], x, nom * 1e6, mc * 1e6, color="C1")
            style_axes(axes_ov[1], r"$V_{SG}$ (V)", r"$|I_D|$ (µA)", f"{model} LOT MC ngspice (n={n:,})")

    ov = PLOTS / "mos_id_vgs_mc.png"
    fig_ov.savefig(ov, dpi=140)
    plt.close(fig_ov)
    outs.insert(0, ov)
    return outs


def plot_bjt_mc(work: Path, n: int = MC_RUNS, workers: int = MC_WORKERS) -> list[Path]:
    """Full ngspice 10k LOT MC for NPN and PNP."""
    MC_DIR.mkdir(parents=True, exist_ok=True)
    outs: list[Path] = []
    fig_ov, axes_ov = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)

    for bi, model in enumerate(BJTS):
        print(f"BJT MC ngspice n={n:,} workers={workers}: {model}", flush=True)
        x, nom, mc = run_spice_mc(
            kind="bjt",
            model=model,
            n=n,
            seed=SEED + 5000 + bi * 1009,
            work_root=work / "mc",
            workers=workers,
        )
        np.savez_compressed(
            MC_DIR / f"{model}_icvbe_mc.npz",
            x=x,
            nominal=nom,
            mc=mc,
            n=n,
            engine="ngspice",
        )
        fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
        plot_mc_band(ax, x, nom, mc, color="C0" if model.startswith("npn") else "C1", logy=True)
        xlab = r"$V_{BE}$ (V)" if model.startswith("npn") else r"$V_{EB}$ (V)"
        style_axes(ax, xlab, r"$|I_C|$ (A)", f"{model} LOT MC ngspice (n={n:,})")
        out = PLOTS / f"mc_{model}_ic_vbe.png"
        fig.savefig(out, dpi=140)
        plt.close(fig)
        outs.append(out)

        ax_ov = axes_ov[0] if model.startswith("npn") else axes_ov[1]
        plot_mc_band(ax_ov, x, nom, mc, color="C0" if model.startswith("npn") else "C1", logy=True)
        style_axes(ax_ov, xlab, r"$|I_C|$ (A)", f"{model} LOT MC ngspice (n={n:,})")

    ov = PLOTS / "bjt_ic_vbe_mc.png"
    fig_ov.savefig(ov, dpi=140)
    plt.close(fig_ov)
    outs.insert(0, ov)
    return outs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mc-only", action="store_true", help="Only run full ngspice MC")
    ap.add_argument("--mc-runs", type=int, default=MC_RUNS)
    ap.add_argument("--workers", type=int, default=MC_WORKERS)
    args = ap.parse_args()

    ensure_ngspice()
    if WORK.exists() and not args.mc_only:
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)
    plt.switch_backend("Agg")

    outs: list[Path] = []
    if not args.mc_only:
        print("MOS Id-Vgs …")
        outs.append(plot_mos_idvg(WORK))
        print("MOS Id-Vds …")
        outs.append(plot_mos_idvd(WORK))
        print("MOS temp …")
        outs.append(plot_mos_temp(WORK))
        print("BJT Ic-Vbe …")
        outs.append(plot_bjt_icvbe(WORK))
        print("BJT temp …")
        outs.append(plot_bjt_temp(WORK))

    print(f"Full ngspice MC: n={args.mc_runs:,} workers={args.workers}")
    outs.extend(plot_mos_mc(WORK, n=args.mc_runs, workers=args.workers))
    outs.extend(plot_bjt_mc(WORK, n=args.mc_runs, workers=args.workers))

    print("Wrote:")
    for p in outs:
        print(" ", p)


if __name__ == "__main__":
    main()
