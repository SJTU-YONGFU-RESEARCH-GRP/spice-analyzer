#!/usr/bin/env python3
"""Run corners, extended specs, extract metrics/hand_tf for fan_smc_pin_3."""
from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from pathlib import Path

RUN = Path("/mnt/d/proj/spice-analyzer-skill/results/fan_smc_pin_3")
ROOT = Path("/mnt/d/proj/spice-analyzer-skill")

VDD = {"cmos": 1.8, "sky130": 1.8, "ihp": 1.2, "gf180": 3.3}


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
    # VINN-drive: LF ~ +/-180; PM ~= phase if phase in (0,180), else 180+ph if ph<0
    if ph >= 0:
        return ph
    return 180.0 + ph


def ngspice(tb_dir: Path, deck: str, log: Path):
    r = subprocess.run(
        ["ngspice", "-b", deck],
        cwd=tb_dir,
        capture_output=True,
        text=True,
    )
    log.write_text(r.stdout + "\n" + r.stderr, encoding="utf-8")
    return r.returncode


def save_nom(b: str):
    sim = RUN / b / "sim"
    fig = RUN / b / "figures"
    for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
        src = sim / f"{f}.txt"
        if src.exists():
            shutil.copy(src, sim / f"{f}_nom.txt")
    for f in ["bode_mag.dat", "bode_phase.dat"]:
        src = fig / f
        if src.exists():
            shutil.copy(src, fig / f.replace(".dat", "_nom.dat"))


def restore_nom(b: str):
    sim = RUN / b / "sim"
    fig = RUN / b / "figures"
    for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
        src = sim / f"{f}_nom.txt"
        if src.exists():
            shutil.copy(src, sim / f"{f}.txt")
    for f in ["bode_mag", "bode_phase"]:
        src = fig / f"{f}_nom.dat"
        if src.exists():
            shutil.copy(src, fig / f"{f}.dat")


def metrics_dict(b: str, tag=""):
    sim = RUN / b / "sim"
    suf = f"_{tag}" if tag else ""
    adc = grab(sim / f"adc{suf}.txt" if tag else sim / "adc.txt")
    ugf = grab(sim / f"ugf{suf}.txt" if tag else sim / "ugf.txt")
    ph = grab(sim / f"ph_at_ugf{suf}.txt" if tag else sim / "ph_at_ugf.txt")
    idd = grab(sim / f"idd{suf}.txt" if tag else sim / "idd.txt")
    pwr = grab(sim / f"power{suf}.txt" if tag else sim / "power.txt")
    vout = grab(sim / f"vout_dc{suf}.txt" if tag else sim / "vout_dc.txt")
    return {
        "adc_dB": adc,
        "ugf_Hz": ugf,
        "ph_ugf_deg": ph,
        "pm_deg": pm_from_phase(ph),
        "idd_A": idd,
        "power_W": pwr,
        "vout_V": vout,
    }


def parse_gm(op_devices: Path):
    """Parse ngspice 'show m' for key devices."""
    if not op_devices.exists():
        return {}
    text = op_devices.read_text(errors="replace")
    # Split by device blocks; look for names containing m8/m9/m10/m11/m23 or xm*
    devices = {}
    blocks = re.split(r"\n(?=Device:|\n[MmXx]\w+\s)", text)
    # simpler line-based: find device name lines then gm=
    cur = None
    for line in text.splitlines():
        m = re.match(r"^(?:Device:\s*)?([mxMX][\w.]+)\b", line.strip())
        if m and ("gm" in line.lower() or line.strip().startswith("m") or line.strip().startswith("M") or line.strip().startswith("x") or line.strip().startswith("X") or "Device" in line):
            # try device header patterns from ngspice show m
            pass
        # ngspice show m format often:
        #  device: xdut.xm8
        # or just lists parameters
        dm = re.search(r"device:\s*(\S+)", line, re.I)
        if dm:
            cur = dm.group(1).lower()
            devices.setdefault(cur, {})
            continue
        if cur:
            for key in ("gm", "gds", "id", "vgs", "vds", "vth", "cgs", "cgd"):
                km = re.search(rf"\b{key}\s*=\s*([+-]?\d+\.?\d*e?[+-]?\d*)", line, re.I)
                if km:
                    devices[cur][key] = float(km.group(1))
    return devices


def pick_dev(devices, substrings):
    for name, d in devices.items():
        if all(s in name for s in substrings):
            return name, d
    # fallback: any containing last substring
    for name, d in devices.items():
        if substrings[-1] in name:
            return name, d
    return None, {}


def write_hand_tf(b: str):
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

    devices = parse_gm(sim / "op_devices.txt")
    # dump keys for debug
    (sim / "op_device_keys.txt").write_text("\n".join(sorted(devices.keys())), encoding="utf-8")

    def gm_of(*parts):
        n, d = pick_dev(devices, parts)
        return d.get("gm"), n, d

    # CMOS uses mm8 etc; PDK uses xdut.xm8
    gm1a, n1a, d1a = gm_of("m8")
    gm1b, n1b, d1b = gm_of("m9")
    gm2, n2, d2 = gm_of("m10")
    gm3, n3, d3 = gm_of("m23")
    gmf, nf, df = gm_of("m11")

    # effective differential gm1 ~ gm of one side (standard)
    gm1 = gm1a if gm1a else gm1b
    if gm1a and gm1b:
        gm1 = 0.5 * (gm1a + gm1b)  # each side; for diff pair Av uses gm of one transistor

    # Actually for PMOS diff pair, stage gm = gm_of_input_device (one side)
    # Prefer single-device gm1a
    if gm1a:
        gm1 = gm1a

    met = metrics_dict(b)
    a0_db = met["adc_dB"] or 80.0
    a0_lin = 10 ** (a0_db / 20.0)

    gm1 = gm1 or 100e-6
    gm2 = gm2 or 200e-6
    gm3 = gm3 or 500e-6
    gmf = gmf or 200e-6

    c1 = 0.2e-12  # parasitic at v2
    gbw = gm1 / (2 * math.pi * c0)
    fp1 = gbw / a0_lin
    fp2 = (gm2 / (2 * math.pi * cl)) * (c0 / c1) if c1 else gm2 / (2 * math.pi * c0)
    # For SMC+FF reduced model used in overlay script — keep keys compatible
    # Prefer topology from hand_notes: fp2~gm2/(2pi Cc), fp3~gm3/(2pi CL), fz~gmf/(2pi Cc)
    fp2 = gm2 / (2 * math.pi * c0)
    fp3 = gm3 / (2 * math.pi * cl)
    fz = gmf / (2 * math.pi * c0)

    lines = [
        f"A0_lin={a0_lin}",
        f"A0_dB={a0_db}",
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
        f"# devices gm1={n1a} gm2={n2} gm3={n3} gmf={nf}",
    ]
    (sim / "hand_tf_params.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "gm1": gm1,
        "gm2": gm2,
        "gm3": gm3,
        "gmf": gmf,
        "c0": c0,
        "gbw_hand": gbw,
        "devices": {"gm1": n1a, "gm2": n2, "gm3": n3, "gmf": nf},
        "gds": {
            "gm1": d1a.get("gds"),
            "gm2": d2.get("gds"),
            "gm3": d3.get("gds"),
            "gmf": df.get("gds"),
        },
        "id": {
            "gm1": d1a.get("id"),
            "gm2": d2.get("id"),
            "gm3": d3.get("id"),
            "gmf": df.get("id"),
        },
    }


def make_corner_deck(b: str, corner: str) -> Path:
    """Create tb_acdc_<corner>.sp from tb_acdc.sp with model corner swap."""
    src = RUN / b / "tb" / "tb_acdc.sp"
    dst = RUN / b / "tb" / f"tb_acdc_{corner}.sp"
    t = src.read_text(encoding="utf-8")
    if b == "sky130":
        # swap tt.pm3 -> ff/ss
        t = t.replace("__tt.pm3.spice", f"__{corner}.pm3.spice")
    elif b == "ihp":
        t = t.replace("mos_tt", f"mos_{corner}")
    elif b == "gf180":
        # typical / ff / ss
        lib = {"tt": "typical", "ff": "ff", "ss": "ss"}[corner]
        t = re.sub(r"sm141064\.ngspice'\s+\w+", f"sm141064.ngspice' {lib}", t)
    dst.write_text(t, encoding="utf-8")
    return dst


def run_corners(b: str):
    rows = []
    for c in ["tt", "ff", "ss"]:
        print(f"corner {b} {c}")
        make_corner_deck(b, c)
        rc = ngspice(RUN / b / "tb", f"tb_acdc_{c}.sp", RUN / b / "sim" / f"acdc_{c}.log")
        sim = RUN / b / "sim"
        fig = RUN / b / "figures"
        for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
            src = sim / f"{f}.txt"
            if src.exists():
                shutil.copy(src, sim / f"{f}_{c}.txt")
        if (fig / "bode_mag.dat").exists():
            shutil.copy(fig / "bode_mag.dat", fig / f"bode_mag_{c}.dat")
        m = metrics_dict(b)
        # overwrite metrics_dict to read just-copied? metrics_dict reads non-suffixed which we just wrote
        m["corner"] = c
        m["rc"] = rc
        rows.append(m)
    restore_nom(b)
    # write corners.csv
    fig = RUN / b / "figures"
    lines = ["corner,adc_dB,ugf_Hz,pm_deg,power_W,vout_V"]
    for r in rows:
        lines.append(
            f"{r['corner']},{r['adc_dB']},{r['ugf_Hz']},{r['pm_deg']},{r['power_W']},{r['vout_V']}"
        )
    (fig / "corners.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (RUN / b / "sim" / "corners.md").write_text(
        "\n".join(
            f"| {r['corner']} | {r['adc_dB']:.2f} | {(r['ugf_Hz'] or 0)/1e6:.3f} | {r['pm_deg']:.1f} | {(r['power_W'] or 0)*1e3:.3f} |"
            for r in rows
        ),
        encoding="utf-8",
    )
    return rows


def run_extended(b: str):
    tb = RUN / b / "tb"
    sim = RUN / b / "sim"
    for deck, tag in [
        ("tb_cmrr.sp", "cmrr"),
        ("tb_psrrp.sp", "psrrp"),
        ("tb_psrrn.sp", "psrrn"),
        ("tb_noise.sp", "noise"),
    ]:
        print(f"ext {b} {deck}")
        ngspice(tb, deck, sim / f"{tag}.log")
    # restore bode from nom if overwritten? CMRR etc write different files
    restore_nom(b)


def main():
    backends = ["cmos", "sky130", "ihp", "gf180"]
    all_met = {}
    all_hand = {}
    all_corners = {}

    for b in backends:
        print("=== save nom", b)
        save_nom(b)
        all_met[b] = metrics_dict(b)
        all_hand[b] = write_hand_tf(b)
        (RUN / b / "sim" / "metrics.json").write_text(
            json.dumps({**all_met[b], "hand": {k: v for k, v in all_hand[b].items() if k != "devices"}}, indent=2),
            encoding="utf-8",
        )

    for b in ["sky130", "ihp", "gf180"]:
        all_corners[b] = run_corners(b)

    for b in backends:
        run_extended(b)
        # rewrite hand_tf after restore
        all_hand[b] = write_hand_tf(b)
        all_met[b] = metrics_dict(b)

    # cross-backend csv
    lines = ["backend,adc_dB,ugf_Hz,pm_deg,power_W"]
    for b in backends:
        m = all_met[b]
        lines.append(f"{b},{m['adc_dB']},{m['ugf_Hz']},{m['pm_deg']},{m['power_W']}")
    (RUN / "figures_cross.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # also put under a shared place plotter expects
    for b in backends:
        shutil.copy(RUN / "figures_cross.csv", RUN / b / "figures" / "figures_cross.csv")

    summary = ["# fan_smc_pin_3 summary", "", "## Nominal", ""]
    summary.append("| Backend | Adc (dB) | UGF (MHz) | PM (deg) | P (mW) | Vout |")
    summary.append("|---------|----------|-----------|----------|--------|------|")
    for b in backends:
        m = all_met[b]
        summary.append(
            f"| {b} | {m['adc_dB']:.2f} | {(m['ugf_Hz'] or 0)/1e6:.3f} | {m['pm_deg']:.1f} | {(m['power_W'] or 0)*1e3:.3f} | {m['vout_V']:.3f} |"
        )
    summary.append("")
    summary.append("## Hand TF gm (OP)")
    for b in backends:
        h = all_hand[b]
        summary.append(
            f"- {b}: gm1={h['gm1']:.3e} gm2={h['gm2']:.3e} gm3={h['gm3']:.3e} gmf={h['gmf']:.3e} GBW_hand={h['gbw_hand']/1e6:.2f} MHz devices={h['devices']}"
        )
    summary.append("")
    summary.append("## Corners")
    for b, rows in all_corners.items():
        summary.append(f"### {b}")
        for r in rows:
            summary.append(
                f"- {r['corner']}: Adc={r['adc_dB']:.1f} UGF={(r['ugf_Hz'] or 0)/1e6:.2f}MHz PM={r['pm_deg']:.1f} P={(r['power_W'] or 0)*1e3:.2f}mW"
            )
    (RUN / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("DONE")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
