#!/usr/bin/env python3
"""Characterize models/opamp.lib (SE + DIFF); write plots under models/plots/."""

from __future__ import annotations

import math
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
LIB = MODELS / "opamp.lib"
PLOTS = MODELS / "plots"
WORK = MODELS / "char" / "opamp_work"
sys.path.insert(0, str(ROOT))
from src.plot_style import (  # noqa: E402
    FIGSIZE,
    LINEWIDTH_MAIN,
    LINEWIDTH_SECONDARY,
    MULTI_SERIES_COLORS,
    apply_rcparams,
    apply_style,
)


def ensure_ngspice() -> list[str]:
    """Prefer WSL ngspice (Linux + OpenVAF path); else local PATH / tools."""
    win = ROOT / "tools" / "Spice64" / "bin" / "ngspice_con.exe"
    # Try native first
    found = shutil.which("ngspice") or shutil.which("ngspice_con")
    if found:
        return [found]
    # WSL
    try:
        r = subprocess.run(
            ["wsl", "-e", "bash", "-lc", "which ngspice"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode == 0 and r.stdout.strip():
            return ["wsl", "-e", "ngspice"]
    except (OSError, subprocess.TimeoutExpired):
        pass
    if win.is_file():
        return [str(win)]
    sys.exit("ngspice not found (PATH, WSL, or tools/Spice64).")


def run_ngspice(deck: Path, cwd: Path) -> None:
    exe = ensure_ngspice()
    cwd.mkdir(parents=True, exist_ok=True)
    log = cwd / (deck.stem + ".log")
    # Under WSL, paths must be Linux-style when cwd is Windows — run via bash cd
    if exe[0] == "wsl":
        # Convert Windows path to /mnt/d/...
        def to_wsl(p: Path) -> str:
            s = str(p.resolve())
            if len(s) >= 2 and s[1] == ":":
                return "/mnt/" + s[0].lower() + s[2:].replace("\\", "/")
            return s.replace("\\", "/")

        wsl_cwd = to_wsl(cwd)
        wsl_deck = deck.name
        cmd = [
            "wsl",
            "-e",
            "bash",
            "-lc",
            f"cd '{wsl_cwd}' && NGSPICE_NO_INIT=1 ngspice -b -a -o '{log.name}' '{wsl_deck}'",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
    else:
        env = {**dict(**__import__("os").environ), "NGSPICE_NO_INIT": "1"}
        cmd = [*exe, "-b", "-a", "-o", str(log.name), str(deck.name)]
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        msg = log.read_text(encoding="utf-8", errors="replace")[-3000:] if log.exists() else (r.stderr or r.stdout)
        raise RuntimeError(f"ngspice failed on {deck.name}\n{msg}")


def read_wrdata(path: Path) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = [], []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith(("*", "#")):
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


def expand_lib() -> str:
    return LIB.read_text(encoding="utf-8")


# Recommended non-ideal defaults (matches opamp.lib). AC decks zero vos so the
# OP is not soft-rail saturated when measuring av0 / GBW.
NONIDEAL = "av0=10k gbw=1meg rin=100meg rout=10k vos=1m acm=10 swing=0.9"
NONIDEAL_AC = "av0=10k gbw=1meg rin=100meg rout=10k vos=0 acm=10 swing=0.9"
IDEAL = "av0=1e6 gbw=100meg rin=1T rout=1m vos=0 acm=0 swing=10"
NONIDEAL_DIFF = NONIDEAL + " vocm=0.9"
NONIDEAL_DIFF_AC = NONIDEAL_AC + " vocm=0.9"
IDEAL_DIFF = IDEAL + " vocm=0.9"


def deck_se_dc(tag: str, params: str) -> str:
    return f"""
* SE DC transfer {tag}
{expand_lib()}
Vdd vdd 0 1.8
Vss vss 0 0
Vic vic 0 0.9
Vid vid 0 0
Einp inp 0 vic vid 1
Einm inm 0 vic 0 1
X1 inp inm out vdd vss opamp_se {params}
.dc Vid -5m 5m 50u
.control
set filetype=ascii
run
wrdata se_dc_{tag}.dat v(out)
.endc
.end
"""


def deck_se_ac(tag: str, params: str) -> str:
    # Truly open-loop AC (vos must be 0 so OP is not saturated).
    return f"""
* SE open-loop AC {tag}
{expand_lib()}
Vdd vdd 0 1.8
Vss vss 0 0
Vic vic 0 0.9
Vin inp 0 dc 0.9 ac 1
Einm inm 0 vic 0 1
X1 inp inm out vdd vss opamp_se {params}
.ac dec 50 1 100meg
.control
set filetype=ascii
run
let mag=db(v(out))
let ph=180/pi*ph(v(out))
wrdata se_ac_mag_{tag}.dat mag
wrdata se_ac_ph_{tag}.dat ph
.endc
.end
"""


def deck_se_buffer(tag: str, params: str) -> str:
    return f"""
* SE unity-gain buffer DC {tag}
{expand_lib()}
Vdd vdd 0 1.8
Vss vss 0 0
Vin inp 0 0.9
X1 inp out out vdd vss opamp_se {params}
.dc Vin 0.2 1.6 0.01
.control
set filetype=ascii
run
wrdata se_buf_{tag}.dat v(out)
.endc
.end
"""


def deck_diff_dc(tag: str, params: str) -> str:
    return f"""
* DIFF DC Vod vs Vid {tag}
{expand_lib()}
Vdd vdd 0 1.8
Vss vss 0 0
Vic vic 0 0.9
Vid vid 0 0
Einp inp 0 vic vid 1
Einm inm 0 vic 0 1
X1 inp inm outp outm vdd vss opamp_diff {params}
.dc Vid -5m 5m 50u
.control
set filetype=ascii
run
let vod=v(outp)-v(outm)
wrdata diff_dc_{tag}.dat vod
.endc
.end
"""


def deck_diff_ac(tag: str, params: str) -> str:
    return f"""
* DIFF open-loop AC {tag}
{expand_lib()}
Vdd vdd 0 1.8
Vss vss 0 0
Vic vic 0 0.9
Vin inp 0 dc 0.9 ac 1
Einm inm 0 vic 0 1
X1 inp inm outp outm vdd vss opamp_diff {params}
Emeas vod 0 outp outm 1
.ac dec 50 1 100meg
.control
set filetype=ascii
run
let mag=db(v(vod))
wrdata diff_ac_mag_{tag}.dat mag
.endc
.end
"""


def deck_cmrr() -> str:
    # vos=0 so SE is not soft-rail locked; shows acm on SE Vout
    # and DIFF output common-mode ((outp+outm)/2).
    return f"""
* SE/DIFF CM sweep (Vid=0, vos=0), non-ideal
{expand_lib()}
Vdd vdd 0 1.8
Vss vss 0 0
Vic vic 0 0.9
Einp inp 0 vic 0 1
Einm inm 0 vic 0 1
Xse inp inm outs vdd vss opamp_se {NONIDEAL_AC}
Xdf inp inm outp outm vdd vss opamp_diff {NONIDEAL_DIFF_AC}
.dc Vic 0.7 1.1 0.01
.control
set filetype=ascii
run
let voc=0.5*(v(outp)+v(outm))
let vod=v(outp)-v(outm)
wrdata cm_se.dat v(outs)
wrdata cm_diff_cm.dat voc
wrdata cm_diff_dm.dat vod
.endc
.end
"""


def find_unity_gain(f: np.ndarray, mag_db: np.ndarray) -> float | None:
    for i in range(1, len(mag_db)):
        if mag_db[i - 1] >= 0 >= mag_db[i]:
            f1, f2 = f[i - 1], f[i]
            m1, m2 = mag_db[i - 1], mag_db[i]
            if m1 == m2:
                return float(f1)
            return float(f1 + (0 - m1) * (f2 - f1) / (m2 - m1))
    return None


def dc_gain_db(vid: np.ndarray, vout: np.ndarray, center: float = 0.0) -> float:
    """Max |dVout/dVid| near `center` (use vos for offset amps)."""
    order = np.argsort(vid)
    v, o = vid[order], vout[order]
    # local slopes
    dv = np.diff(v)
    g = np.diff(o) / np.where(np.abs(dv) < 1e-18, np.nan, dv)
    vc = 0.5 * (v[1:] + v[:-1])
    window = np.abs(vc - center) < 80e-6
    if not np.any(window):
        window = np.abs(vc - center) < 200e-6
    if not np.any(window):
        gain = float(np.nanmax(np.abs(g)))
    else:
        gain = float(np.nanmax(np.abs(g[window])))
    return 20 * math.log10(abs(gain) + 1e-30)


def main() -> None:
    apply_rcparams()
    PLOTS.mkdir(parents=True, exist_ok=True)
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    jobs = [
        ("se_dc_nonideal", deck_se_dc("nonideal", NONIDEAL)),
        ("se_dc_ideal", deck_se_dc("ideal", IDEAL)),
        ("se_ac_nonideal", deck_se_ac("nonideal", NONIDEAL_AC)),
        ("se_ac_ideal", deck_se_ac("ideal", IDEAL)),
        ("se_buf_nonideal", deck_se_buffer("nonideal", NONIDEAL)),
        ("se_buf_ideal", deck_se_buffer("ideal", IDEAL)),
        ("diff_dc_nonideal", deck_diff_dc("nonideal", NONIDEAL_DIFF)),
        ("diff_dc_ideal", deck_diff_dc("ideal", IDEAL_DIFF)),
        ("diff_ac_nonideal", deck_diff_ac("nonideal", NONIDEAL_DIFF_AC)),
        ("diff_ac_ideal", deck_diff_ac("ideal", IDEAL_DIFF)),
        ("cmrr", deck_cmrr()),
    ]

    metrics: dict[str, float] = {}
    for name, body in jobs:
        path = WORK / f"{name}.sp"
        write_deck(path, body)
        print(f"run {name} ...")
        run_ngspice(path, WORK)

    # --- plots ---
    c0, c1, c2 = MULTI_SERIES_COLORS

    # DC SE
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for tag, color, lw in (("nonideal", c0, LINEWIDTH_MAIN), ("ideal", c1, LINEWIDTH_SECONDARY)):
        x, y = read_wrdata(WORK / f"se_dc_{tag}.dat")
        ax.plot(x * 1e3, y, color=color, lw=lw, label=tag)
    ax.set_xlabel("Vid [mV]")
    ax.set_ylabel("Vout [V]")
    ax.set_title("SE opamp DC transfer (Vic=0.9 V; nonideal vos=1 mV)")
    ax.legend()
    apply_style(ax)
    fig.tight_layout()
    fig.savefig(PLOTS / "opamp_se_dc.png", dpi=150)
    plt.close(fig)

    # AC SE
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for tag, color, lw in (("nonideal", c0, LINEWIDTH_MAIN), ("ideal", c1, LINEWIDTH_SECONDARY)):
        f, mag = read_wrdata(WORK / f"se_ac_mag_{tag}.dat")
        ax.semilogx(f, mag, color=color, lw=lw, label=tag)
        ug = find_unity_gain(f, mag)
        if ug is not None:
            metrics[f"se_gbw_{tag}_Hz"] = ug
            ax.axvline(ug, color=color, ls="--", lw=1.2, alpha=0.7)
        metrics[f"se_av0_{tag}_dB"] = float(mag[0])
    ax.axhline(0, color="#444", lw=1, alpha=0.5)
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("|A| [dB]")
    ax.set_title("SE open-loop gain")
    ax.legend()
    apply_style(ax)
    fig.tight_layout()
    fig.savefig(PLOTS / "opamp_se_ac.png", dpi=150)
    plt.close(fig)

    # Buffer
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for tag, color, lw in (("nonideal", c0, LINEWIDTH_MAIN), ("ideal", c1, LINEWIDTH_SECONDARY)):
        x, y = read_wrdata(WORK / f"se_buf_{tag}.dat")
        ax.plot(x, y, color=color, lw=lw, label=tag)
        err = y - x
        metrics[f"se_buf_maxabs_err_{tag}_mV"] = float(np.max(np.abs(err)) * 1e3)
    ax.plot([0.2, 1.6], [0.2, 1.6], color="#888", ls=":", lw=1.5, label="y=x")
    ax.set_xlabel("Vin [V]")
    ax.set_ylabel("Vout [V]")
    ax.set_title("SE unity-gain buffer")
    ax.legend()
    apply_style(ax)
    fig.tight_layout()
    fig.savefig(PLOTS / "opamp_se_buffer.png", dpi=150)
    plt.close(fig)

    # DIFF DC
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for tag, color, lw in (("nonideal", c0, LINEWIDTH_MAIN), ("ideal", c1, LINEWIDTH_SECONDARY)):
        x, y = read_wrdata(WORK / f"diff_dc_{tag}.dat")
        ax.plot(x * 1e3, y, color=color, lw=lw, label=tag)
    ax.set_xlabel("Vid [mV]")
    ax.set_ylabel("Vod = Outp-Outm [V]")
    ax.set_title("DIFF opamp DC transfer (nonideal vos=1 mV)")
    ax.legend()
    apply_style(ax)
    fig.tight_layout()
    fig.savefig(PLOTS / "opamp_diff_dc.png", dpi=150)
    plt.close(fig)

    # DIFF AC
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for tag, color, lw in (("nonideal", c0, LINEWIDTH_MAIN), ("ideal", c1, LINEWIDTH_SECONDARY)):
        f, mag = read_wrdata(WORK / f"diff_ac_mag_{tag}.dat")
        ax.semilogx(f, mag, color=color, lw=lw, label=tag)
        ug = find_unity_gain(f, mag)
        if ug is not None:
            metrics[f"diff_gbw_{tag}_Hz"] = ug
        metrics[f"diff_av0_{tag}_dB"] = float(mag[0])
    ax.axhline(0, color="#444", lw=1, alpha=0.5)
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("|Ad| [dB]")
    ax.set_title("DIFF open-loop differential gain")
    ax.legend()
    apply_style(ax)
    fig.tight_layout()
    fig.savefig(PLOTS / "opamp_diff_ac.png", dpi=150)
    plt.close(fig)

    # CM sensitivity
    fig, ax = plt.subplots(figsize=FIGSIZE)
    x, yse = read_wrdata(WORK / "cm_se.dat")
    _, ycm = read_wrdata(WORK / "cm_diff_cm.dat")
    _, ydm = read_wrdata(WORK / "cm_diff_dm.dat")
    ax.plot(x, yse, color=c0, lw=LINEWIDTH_MAIN, label="SE Vout")
    ax.plot(x, ycm, color=c1, lw=LINEWIDTH_MAIN, label="DIFF Voc")
    ax.plot(x, ydm, color=c2, lw=LINEWIDTH_SECONDARY, label="DIFF Vod")
    metrics["se_acm_slope"] = float((yse[-1] - yse[0]) / (x[-1] - x[0]))
    metrics["diff_acm_voc_slope"] = float((ycm[-1] - ycm[0]) / (x[-1] - x[0]))
    metrics["diff_cm_to_dm_slope"] = float((ydm[-1] - ydm[0]) / (x[-1] - x[0]))
    ax.set_xlabel("Vic [V]")
    ax.set_ylabel("Output [V]")
    ax.set_title("Common-mode sweep (Vid=0, vos=0), non-ideal")
    ax.legend()
    apply_style(ax)
    fig.tight_layout()
    fig.savefig(PLOTS / "opamp_cm.png", dpi=150)
    plt.close(fig)

    summary = WORK / "metrics.txt"
    lines = ["# opamp characterization metrics", ""]
    for k in sorted(metrics):
        lines.append(f"{k} = {metrics[k]:.6g}")
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nplots -> {PLOTS}")
    print(f"metrics -> {summary}")


if __name__ == "__main__":
    main()
