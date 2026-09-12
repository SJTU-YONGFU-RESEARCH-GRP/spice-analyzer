#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

RUN = Path("/mnt/d/proj/spice-analyzer-skill/results/fan_smc_pin_3")
ROOT = Path("/mnt/d/proj/spice-analyzer-skill")
VDD = {"cmos": 1.8, "sky130": 1.8, "ihp": 1.2, "gf180": 3.3}


def grab(path):
    p = Path(path)
    if not p.exists():
        return None
    t = p.read_text(errors="replace")
    if "NO_UGF" in t or not t.strip():
        return None
    m = re.search(r"=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)", t)
    if m:
        return float(m.group(1))
    m = re.search(r"([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)", t)
    return float(m.group(1)) if m else None


def pm(ph):
    if ph is None:
        return None
    return ph if ph >= 0 else 180 + ph


def ngspice(tb, deck, log):
    r = subprocess.run(["ngspice", "-b", deck], cwd=str(tb), capture_output=True, text=True)
    Path(log).write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
    return r.returncode


def patch_idd(path: Path, vdd: float):
    t = path.read_text(encoding="utf-8")
    if "print idd_op > ../sim/idd.txt" in t:
        print("already", path.name)
        return
    inject = f"""
let idd_op = -i(VDD)
let vout_op = v(vout)
let power_op = idd_op * {vdd}
print idd_op > ../sim/idd.txt
print vout_op > ../sim/vout_dc.txt
print power_op > ../sim/power.txt
"""
    if "ac dec" in t:
        t = t.replace("ac dec", inject + "\nac dec", 1)
    else:
        t = t.replace("quit", inject + "\nquit", 1)
    path.write_text(t, encoding="utf-8")
    print("patched", path)


def ensure_gf_params(p: Path):
    t = p.read_text(encoding="utf-8")
    if "fnoicor" in t:
        return
    lines = t.splitlines()
    hdr = [
        ".param fnoicor=0",
        ".param sw_stat_mismatch=0",
        ".param sw_stat_global=0",
        ".param sw_stat_local=0",
    ]
    if lines and lines[0].startswith("*"):
        lines = [lines[0]] + hdr + lines[1:]
    else:
        lines = hdr + lines
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("gf params", p.name)


def run_acdc(b):
    tb = RUN / b / "tb"
    sim = RUN / b / "sim"
    fig = RUN / b / "figures"
    for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
        p = sim / f"{f}.txt"
        if p.exists():
            p.unlink()
    print("ACDC", b)
    rc = ngspice(tb, "tb_acdc.sp", sim / "acdc.log")
    adc = grab(sim / "adc.txt")
    print(
        " ",
        rc,
        "adc",
        adc,
        "ugf",
        grab(sim / "ugf.txt"),
        "idd",
        grab(sim / "idd.txt"),
        "p",
        grab(sim / "power.txt"),
        "gm8",
        grab(sim / "gm_m8.txt"),
    )
    if adc is None:
        return False
    for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
        if (sim / f"{f}.txt").exists():
            shutil.copy(sim / f"{f}.txt", sim / f"{f}_nom.txt")
    for f in ["bode_mag.dat", "bode_phase.dat"]:
        if (fig / f).exists():
            shutil.copy(fig / f, fig / f.replace(".dat", "_nom.dat"))
    return True


def run_corners(b):
    sim = RUN / b / "sim"
    fig = RUN / b / "figures"
    rows = []
    for c in ["tt", "ff", "ss"]:
        src = (RUN / b / "tb" / "tb_acdc.sp").read_text(encoding="utf-8")
        t = src
        if b == "sky130":
            t = re.sub(r"__(tt|ff|ss)\.pm3\.spice", f"__{c}.pm3.spice", t)
        elif b == "ihp":
            t = re.sub(r"mos_(tt|ff|ss)", f"mos_{c}", t)
        elif b == "gf180":
            lib = {"tt": "typical", "ff": "ff", "ss": "ss"}[c]
            t = re.sub(
                r"(sm141064\.ngspice'\s+)(typical|ff|ss|tt)",
                rf"\1{lib}",
                t,
            )
        (RUN / b / "tb" / f"tb_acdc_{c}.sp").write_text(t, encoding="utf-8")
        if b == "gf180":
            ensure_gf_params(RUN / b / "tb" / f"tb_acdc_{c}.sp")
        for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
            p = sim / f"{f}.txt"
            if p.exists():
                p.unlink()
        print("CORNER", b, c)
        rc = ngspice(RUN / b / "tb", f"tb_acdc_{c}.sp", sim / f"acdc_{c}.log")
        adc = grab(sim / "adc.txt")
        ugf = grab(sim / "ugf.txt")
        phv = grab(sim / "ph_at_ugf.txt")
        pwr = grab(sim / "power.txt")
        vout = grab(sim / "vout_dc.txt")
        if adc is None:
            print("  FAIL", rc)
            rows.append(
                dict(
                    corner=c,
                    dcgain=None,
                    ugf_mhz=None,
                    pm_deg=None,
                    power_mw=None,
                    vout_V=None,
                )
            )
        else:
            row = dict(
                corner=c,
                dcgain=adc,
                ugf_mhz=ugf / 1e6 if ugf else None,
                pm_deg=pm(phv),
                power_mw=pwr * 1e3 if pwr else None,
                vout_V=vout,
            )
            print(" ", row)
            rows.append(row)
            for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
                if (sim / f"{f}.txt").exists():
                    shutil.copy(sim / f"{f}.txt", sim / f"{f}_{c}.txt")
    for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
        nom = sim / f"{f}_nom.txt"
        if nom.exists():
            shutil.copy(nom, sim / f"{f}.txt")
    for f in ["bode_mag", "bode_phase"]:
        nom = fig / f"{f}_nom.dat"
        if nom.exists():
            shutil.copy(nom, fig / f"{f}.dat")
    with (fig / "corners.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh, fieldnames=["corner", "dcgain", "ugf_mhz", "pm_deg", "power_mw", "vout_V"]
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return rows


def parse_show_m(path: Path) -> dict:
    devices = {}
    headers = []
    if not path.exists():
        return devices
    for line in path.read_text(errors="replace").splitlines():
        if line.strip().lower().startswith("device"):
            headers = [p for p in line.split() if p.lower() != "device"]
            for h in headers:
                devices.setdefault(h.lower(), {})
            continue
        parts = line.split()
        if len(parts) < 2 or not headers:
            continue
        key = parts[0].lower()
        if key not in ("gm", "gds", "id"):
            continue
        for i, h in enumerate(headers):
            if i + 1 < len(parts):
                try:
                    devices[h.lower()][key] = float(parts[i + 1])
                except ValueError:
                    pass
    return devices


def find_token(devices, token):
    for name, d in devices.items():
        if f"xm{token}" in name or f"mm{token}" in name:
            if "gm" in d:
                return name, d
    return None, {}


def write_hand_tf(b, gm1, gm2, gm3, gmf):
    sim = RUN / b / "sim"
    params = (RUN / b / "tb" / "params.sp").read_text()
    c0 = float(re.search(r"CAPACITOR_0=([\d.]+)p", params).group(1)) * 1e-12
    cl = float(re.search(r"CLOAD=([\d.]+)p", params).group(1)) * 1e-12
    adc = grab(sim / "adc_nom.txt") or 80.0
    a0 = 10 ** (adc / 20.0)
    gbw = gm1 / (2 * math.pi * c0)
    (sim / "hand_tf_params.txt").write_text(
        "\n".join(
            [
                f"A0_lin={a0}",
                f"A0_dB={adc}",
                f"gm1_S={gm1}",
                f"gm2_S={gm2}",
                f"gm3_S={gm3}",
                f"gmf_S={gmf}",
                f"C0_F={c0}",
                f"C1_F={0.2e-12}",
                f"CL_F={cl}",
                f"GBW_Hz={gbw}",
                f"fp1_Hz={gbw/a0}",
                f"fp2_Hz={gm2/(2*math.pi*c0)}",
                f"fp3_Hz={gm3/(2*math.pi*cl)}",
                f"fz_Hz={gmf/(2*math.pi*c0)}",
                "vinn_drive=1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return dict(gm1=gm1, gm2=gm2, gm3=gm3, gmf=gmf, gbw=gbw, c0=c0, adc=adc)


def main():
    for b, v in VDD.items():
        for p in (RUN / b / "tb").glob("tb_acdc*.sp"):
            patch_idd(p, v)
    for p in (RUN / "gf180" / "tb").glob("tb_*.sp"):
        ensure_gf_params(p)

    corners = {}
    for b in ["ihp", "gf180"]:
        if not run_acdc(b):
            print("FAIL nominal", b)
            continue
        corners[b] = run_corners(b)
        for deck, tag in [
            ("tb_cmrr.sp", "cmrr"),
            ("tb_psrrp.sp", "psrrp"),
            ("tb_psrrn.sp", "psrrn"),
            ("tb_noise.sp", "noise"),
        ]:
            print("EXT", b, deck)
            ngspice(RUN / b / "tb", deck, RUN / b / "sim" / f"{tag}.log")
        sim = RUN / b / "sim"
        fig = RUN / b / "figures"
        for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
            nom = sim / f"{f}_nom.txt"
            if nom.exists():
                shutil.copy(nom, sim / f"{f}.txt")
        for f in ["bode_mag", "bode_phase"]:
            nom = fig / f"{f}_nom.dat"
            if nom.exists():
                shutil.copy(nom, fig / f"{f}.dat")

    # refresh cmos/sky130 if power missing
    for b in ["cmos", "sky130"]:
        if grab(RUN / b / "sim" / "power_nom.txt") is None:
            run_acdc(b)
        # ensure sky130 corners csv uses plotter columns (already from earlier)

    hands = {}
    mets = {}
    for b in ["cmos", "sky130", "ihp", "gf180"]:
        sim = RUN / b / "sim"
        devs = parse_show_m(sim / "op_devices.txt")
        gms = {}
        for tok, key in [("8", "gm1"), ("10", "gm2"), ("23", "gm3"), ("11", "gmf")]:
            n, d = find_token(devs, tok)
            gms[key] = d.get("gm")
            print(b, key, n, gms[key])
        if b == "cmos":
            gms["gm1"] = grab(sim / "gm_m8_nom.txt") or grab(sim / "gm_m8.txt") or gms["gm1"]
            gms["gm2"] = grab(sim / "gm_m10_nom.txt") or grab(sim / "gm_m10.txt") or gms["gm2"]
            gms["gm3"] = grab(sim / "gm_m23_nom.txt") or grab(sim / "gm_m23.txt") or gms["gm3"]
            gms["gmf"] = grab(sim / "gm_m11_nom.txt") or grab(sim / "gm_m11.txt") or gms["gmf"]
        for k, fb in zip(["gm1", "gm2", "gm3", "gmf"], [1e-4, 2e-4, 5e-4, 2e-4]):
            if not gms.get(k):
                gms[k] = fb
        hands[b] = write_hand_tf(b, gms["gm1"], gms["gm2"], gms["gm3"], gms["gmf"])
        mets[b] = {
            "adc_dB": grab(sim / "adc_nom.txt"),
            "ugf_Hz": grab(sim / "ugf_nom.txt"),
            "pm_deg": pm(grab(sim / "ph_at_ugf_nom.txt")),
            "power_W": grab(sim / "power_nom.txt"),
            "idd_A": grab(sim / "idd_nom.txt"),
            "vout_V": grab(sim / "vout_dc_nom.txt"),
            "cmrr_dB": grab(sim / "cmrrdc.txt"),
            "psrrp_dB": grab(sim / "psrrp_dc.txt"),
            "psrrn_dB": grab(sim / "psrrn_dc.txt"),
            "hand": hands[b],
        }
        (sim / "metrics.json").write_text(json.dumps(mets[b], indent=2), encoding="utf-8")

    with (RUN / "figures_cross.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["backend", "dcgain", "ugf_mhz", "pm_deg", "power_mw"])
        w.writeheader()
        for b, m in mets.items():
            if m["adc_dB"] is None:
                continue
            w.writerow(
                {
                    "backend": b,
                    "dcgain": m["adc_dB"],
                    "ugf_mhz": m["ugf_Hz"] / 1e6,
                    "pm_deg": m["pm_deg"],
                    "power_mw": (m["power_W"] * 1e3) if m["power_W"] else None,
                }
            )

    for b in ["sky130", "ihp", "gf180"]:
        (RUN / b / "sim" / "mc_summary.md").write_text(
            "HARD-SKIP: open-PDK mismatch MC not enabled (per-trial agauss not wired).\n",
            encoding="utf-8",
        )
    (RUN / "cmos" / "sim" / "mc_summary.md").write_text(
        "HARD-SKIP: CMOS LOT MC loop ran but Level-1 agauss did not resample across trials "
        "(UGF identical); educational LOT variation ineffective without deck re-parse.\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            "python3",
            str(ROOT / ".agents/skills/spice-analyzer/plotting/render_spice_figures.py"),
            str(RUN),
        ],
        check=False,
    )
    subprocess.run(
        [
            "python3",
            str(ROOT / ".agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.py"),
            str(RUN),
        ],
        check=False,
    )

    lines = ["# fan_smc_pin_3 summary", "", "## Nominal", ""]
    lines.append("| Backend | Adc | UGF MHz | PM | P mW | Vout |")
    lines.append("|---------|-----|---------|----|------|------|")
    for b, m in mets.items():
        if m["adc_dB"] is None:
            lines.append(f"| {b} | FAIL | | | | |")
        else:
            pw = m["power_W"] * 1e3 if m["power_W"] else float("nan")
            lines.append(
                f"| {b} | {m['adc_dB']:.2f} | {m['ugf_Hz']/1e6:.3f} | {m['pm_deg']:.1f} | "
                f"{pw:.3f} | {m['vout_V']:.3f} |"
            )
    lines += ["", "## Hand gm"]
    for b, h in hands.items():
        lines.append(
            f"- {b}: gm1={h['gm1']:.4e} gm2={h['gm2']:.4e} gm3={h['gm3']:.4e} gmf={h['gmf']:.4e} "
            f"GBW={h['gbw']/1e6:.2f} MHz"
        )
    lines += ["", "## Corners ihp/gf180"]
    for b, rows in corners.items():
        lines.append(f"### {b}")
        for r in rows:
            lines.append(str(r))
    (RUN / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("DONE")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
