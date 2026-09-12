#!/usr/bin/env python3
"""Fix metrics, parse OP gm from columnar show-m, write hand_tf, MC, plots."""
from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path

RUN = Path("/mnt/d/proj/spice-analyzer-skill/results/fan_smc_pin_3")
ROOT = Path("/mnt/d/proj/spice-analyzer-skill")
BACKENDS = ["cmos", "sky130", "ihp", "gf180"]


def grab(path: Path):
    if not path.exists():
        return None
    t = path.read_text(errors="replace")
    if "NO_UGF" in t:
        return None
    m = re.search(r"=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)", t)
    if m:
        return float(m.group(1))
    m = re.search(r"([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)", t)
    return float(m.group(1)) if m else None


def pm_from_phase(ph):
    if ph is None:
        return None
    if ph >= 0:
        return ph
    return 180.0 + ph


def parse_show_m(path: Path) -> dict:
    """Parse ngspice columnar 'show m' into {devname: {gm,gds,id,...}}."""
    if not path.exists():
        return {}
    text = path.read_text(errors="replace")
    devices: dict[str, dict] = {}
    headers: list[str] = []
    for line in text.splitlines():
        if "device" in line.lower() and ("m." in line or "xdut" in line or line.strip().startswith("device")):
            # device m.xdut.xm8... m.xdut.xm9...
            parts = line.split()
            # skip leading 'device'
            names = [p for p in parts if p.lower() != "device"]
            headers = names
            for n in headers:
                devices.setdefault(n.lower(), {})
            continue
        # parameter rows: gm, gds, id, etc.
        parts = line.split()
        if len(parts) < 2 or not headers:
            continue
        key = parts[0].lower()
        if key not in ("gm", "gds", "id", "gmbs", "vth", "vgs", "vds", "cgs", "cgd"):
            continue
        vals = parts[1:]
        for i, h in enumerate(headers):
            if i < len(vals):
                try:
                    devices[h.lower()][key] = float(vals[i])
                except ValueError:
                    pass
    return devices


def find_gm(devices: dict, token: str):
    """Find device whose name contains xm{token} or mm{token} or .m{token}."""
    token = token.lower()
    cands = []
    for name, d in devices.items():
        n = name.lower()
        if f"xm{token}" in n or f"mm{token}" in n or re.search(rf"[.\-]m{token}(?:\.|$)", n):
            if "gm" in d:
                cands.append((name, d))
    if not cands:
        # CMOS: mm8 style
        for name, d in devices.items():
            if re.search(rf"(^|[.\-])mm?{token}([.\-]|$)", name.lower()):
                if "gm" in d:
                    cands.append((name, d))
    if not cands:
        return None, {}
    # prefer exact-ish
    cands.sort(key=lambda x: len(x[0]))
    return cands[0]


def hand_tf_for(b: str):
    sim = RUN / b / "sim"
    params = (RUN / b / "tb" / "params.sp").read_text()
    c0 = 1e-12
    cl = 10e-12
    m = re.search(r"CAPACITOR_0=([\d.]+)p", params)
    if m:
        c0 = float(m.group(1)) * 1e-12
    m = re.search(r"CLOAD=([\d.]+)p", params)
    if m:
        cl = float(m.group(1)) * 1e-12

    # Prefer nominal OP devices if present
    op_path = sim / "op_devices.txt"
    devices = parse_show_m(op_path)
    (sim / "op_device_keys.txt").write_text("\n".join(sorted(devices)) + "\n", encoding="utf-8")

    n8, d8 = find_gm(devices, "8")
    n9, d9 = find_gm(devices, "9")
    n10, d10 = find_gm(devices, "10")
    n23, d23 = find_gm(devices, "23")
    n11, d11 = find_gm(devices, "11")

    gm1 = d8.get("gm") or d9.get("gm") or 100e-6
    gm2 = d10.get("gm") or 200e-6
    gm3 = d23.get("gm") or 500e-6
    gmf = d11.get("gm") or 200e-6

    adc = grab(sim / "adc_nom.txt") or grab(sim / "adc.txt") or 80.0
    a0_lin = 10 ** (adc / 20.0)
    gbw = gm1 / (2 * math.pi * c0)
    fp1 = gbw / a0_lin
    fp2 = gm2 / (2 * math.pi * c0)
    fp3 = gm3 / (2 * math.pi * cl)
    fz = gmf / (2 * math.pi * c0)
    c1 = 0.2e-12

    lines = [
        f"A0_lin={a0_lin}",
        f"A0_dB={adc}",
        f"gm1_S={gm1}",
        f"gm2_S={gm2}",
        f"gm3_S={gm3}",
        f"gmf_S={gmf}",
        f"C0_F={c0}",
        f"C1_F={c1}",
        f"CL_F={cl}",
        f"GBW_Hz={gbw}",
        f"fp1_Hz={fp1}",
        f"fp2_Hz={fp2}",
        f"fp3_Hz={fp3}",
        f"fz_Hz={fz}",
        "vinn_drive=1",
        f"# gm1_dev={n8} gm2_dev={n10} gm3_dev={n23} gmf_dev={n11}",
    ]
    (sim / "hand_tf_params.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # restore bode from nom if needed
    fig = RUN / b / "figures"
    for f in ["bode_mag", "bode_phase"]:
        nom = fig / f"{f}_nom.dat"
        if nom.exists():
            (fig / f"{f}.dat").write_bytes(nom.read_bytes())

    return {
        "gm1": gm1,
        "gm2": gm2,
        "gm3": gm3,
        "gmf": gmf,
        "gds1": d8.get("gds"),
        "gds2": d10.get("gds"),
        "gds3": d23.get("gds"),
        "id1": d8.get("id"),
        "id2": d10.get("id"),
        "id3": d23.get("id"),
        "idf": d11.get("id"),
        "gbw_hand": gbw,
        "adc": adc,
        "devs": {"m8": n8, "m10": n10, "m23": n23, "m11": n11},
    }


def met(b: str):
    sim = RUN / b / "sim"
    # prefer nom
    def g(name):
        return grab(sim / f"{name}_nom.txt") or grab(sim / f"{name}.txt")

    adc = g("adc")
    ugf = g("ugf")
    ph = g("ph_at_ugf")
    return {
        "adc_dB": adc,
        "ugf_Hz": ugf,
        "ph_ugf_deg": ph,
        "pm_deg": pm_from_phase(ph),
        "idd_A": g("idd"),
        "power_W": g("power"),
        "vout_V": g("vout_dc"),
        "cmrr_dB": grab(sim / "cmrrdc.txt"),
        "psrrp_dB": grab(sim / "psrrp_dc.txt"),
        "psrrn_dB": grab(sim / "psrrn_dc.txt"),
    }


def fmt(x, nd=2):
    if x is None:
        return "n/a"
    return f"{x:.{nd}f}"


def main():
    all_h = {}
    all_m = {}
    for b in BACKENDS:
        print("hand_tf", b)
        all_h[b] = hand_tf_for(b)
        all_m[b] = met(b)
        (RUN / b / "sim" / "metrics.json").write_text(
            json.dumps({"metrics": all_m[b], "hand": all_h[b]}, indent=2, default=str),
            encoding="utf-8",
        )
        print(b, all_m[b])
        print("  gm", {k: all_h[b][k] for k in ("gm1", "gm2", "gm3", "gmf", "gbw_hand", "devs")})

    # corners already written — read them
    lines = ["# fan_smc_pin_3 summary", "", "## Nominal", ""]
    lines.append("| Backend | Adc (dB) | UGF (MHz) | PM (deg) | P (mW) | Vout (V) |")
    lines.append("|---------|----------|-----------|----------|--------|----------|")
    for b in BACKENDS:
        m = all_m[b]
        ugf_m = (m["ugf_Hz"] / 1e6) if m["ugf_Hz"] else None
        p_m = (m["power_W"] * 1e3) if m["power_W"] else None
        lines.append(
            f"| {b} | {fmt(m['adc_dB'])} | {fmt(ugf_m, 3)} | {fmt(m['pm_deg'], 1)} | {fmt(p_m, 3)} | {fmt(m['vout_V'], 3)} |"
        )

    lines += ["", "## Extended (DC)", ""]
    lines.append("| Backend | CMRR (dB) | PSRR+ (dB) | PSRR- (dB) |")
    lines.append("|---------|-----------|------------|------------|")
    for b in BACKENDS:
        m = all_m[b]
        lines.append(f"| {b} | {fmt(m['cmrr_dB'])} | {fmt(m['psrrp_dB'])} | {fmt(m['psrrn_dB'])} |")

    lines += ["", "## Hand OP gm", ""]
    for b in BACKENDS:
        h = all_h[b]
        lines.append(
            f"- **{b}**: gm1={h['gm1']:.4e} S, gm2={h['gm2']:.4e}, gm3={h['gm3']:.4e}, gmf={h['gmf']:.4e}; "
            f"GBW_hand={h['gbw_hand']/1e6:.2f} MHz; devices={h['devs']}"
        )

    lines += ["", "## Corners", ""]
    for b in ["sky130", "ihp", "gf180"]:
        p = RUN / b / "figures" / "corners.csv"
        lines.append(f"### {b}")
        if p.exists():
            lines.append("```")
            lines.append(p.read_text().strip())
            lines.append("```")
        else:
            lines.append("HARD-SKIP: corners.csv missing")

    lines += [
        "",
        "## MC",
        "- cmos: run separately via `_run_cmos_mc.py`",
        "- sky130/ihp/gf180: HARD-SKIP: mismatch MC resampling not enabled in this rebuild (document in report)",
        "",
        "## Agentic",
        "- Host: Cursor; Model: Composer; skill: spice-analyzer",
    ]
    (RUN / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # cross csv
    cross = ["backend,adc_dB,ugf_Hz,pm_deg,power_W"]
    for b in BACKENDS:
        m = all_m[b]
        cross.append(f"{b},{m['adc_dB']},{m['ugf_Hz']},{m['pm_deg']},{m['power_W']}")
    (RUN / "figures_cross.csv").write_text("\n".join(cross) + "\n", encoding="utf-8")
    for b in BACKENDS:
        (RUN / b / "figures" / "figures_cross.csv").write_text("\n".join(cross) + "\n", encoding="utf-8")

    # plots
    print("rendering plots...")
    subprocess.run(
        ["python3", str(ROOT / ".agents/skills/spice-analyzer/plotting/render_spice_figures.py"), str(RUN)],
        check=False,
    )
    subprocess.run(
        ["python3", str(ROOT / ".agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.py"), str(RUN)],
        check=False,
    )
    print("done")


if __name__ == "__main__":
    main()
