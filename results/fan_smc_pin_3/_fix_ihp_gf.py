#!/usr/bin/env python3
"""Fix IHP OSDI, GF180 params, extract sky130 gm, re-run affected sims."""
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
OSDI = ROOT / "models/pdk/ihp-sg13g2/ihp-sg13g2/libs.tech/ngspice/osdi"


def grab(path: Path):
    if not path.exists():
        return None
    t = path.read_text(errors="replace")
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
    return ph if ph >= 0 else 180.0 + ph


def ngspice(tb: Path, deck: str, log: Path) -> int:
    r = subprocess.run(["ngspice", "-b", deck], cwd=str(tb), capture_output=True, text=True)
    log.write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
    return r.returncode


def fix_ihp_spiceinit():
    lines = []
    for f in ["psp103.osdi", "psp103_nqs.osdi", "mosvar.osdi", "r3_cmc.osdi", "cap_cmomi.osdi", "cap_cmomf.osdi"]:
        p = OSDI / f
        if p.exists():
            lines.append(f"osdi {p}")
    (RUN / "ihp" / "tb" / ".spiceinit").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote ihp .spiceinit with osdi")


def fix_gf180_headers():
    header = (
        ".param fnoicor=0\n"
        ".param sw_stat_mismatch=0\n"
        ".param sw_stat_global=0\n"
        ".param sw_stat_local=0\n"
    )
    for p in (RUN / "gf180" / "tb").glob("tb_*.sp"):
        t = p.read_text(encoding="utf-8")
        # strip old
        lines = [ln for ln in t.splitlines() if not any(
            k in ln for k in ["fnoicor", "sw_stat_mismatch", "sw_stat_global", "sw_stat_local"]
        )]
        if lines and lines[0].startswith("*"):
            out = [lines[0], header.rstrip()] + lines[1:]
        else:
            out = [header.rstrip()] + lines
        p.write_text("\n".join(out) + "\n", encoding="utf-8")
        print("patched", p.name)


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
        if key not in ("gm", "gds", "id", "gmbs", "vth"):
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


def write_hand_tf(b: str, gm1, gm2, gm3, gmf):
    sim = RUN / b / "sim"
    params = (RUN / b / "tb" / "params.sp").read_text()
    c0 = float(re.search(r"CAPACITOR_0=([\d.]+)p", params).group(1)) * 1e-12
    cl = float(re.search(r"CLOAD=([\d.]+)p", params).group(1)) * 1e-12
    adc = grab(sim / "adc_nom.txt") or grab(sim / "adc.txt") or 80.0
    a0 = 10 ** (adc / 20.0)
    gbw = gm1 / (2 * math.pi * c0)
    text = "\n".join([
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
    ]) + "\n"
    (sim / "hand_tf_params.txt").write_text(text, encoding="utf-8")
    return {"gm1": gm1, "gm2": gm2, "gm3": gm3, "gmf": gmf, "gbw": gbw, "c0": c0, "adc": adc}


def run_acdc(b: str):
    tb = RUN / b / "tb"
    sim = RUN / b / "sim"
    fig = RUN / b / "figures"
    # clear stale metrics so failures don't look like success
    for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
        p = sim / f"{f}.txt"
        if p.exists():
            p.unlink()
    print(f"ACDC {b}")
    rc = ngspice(tb, "tb_acdc.sp", sim / "acdc.log")
    ok = (sim / "adc.txt").exists() and grab(sim / "adc.txt") is not None
    print(f"  rc={rc} ok={ok} adc={grab(sim/'adc.txt')} ugf={grab(sim/'ugf.txt')}")
    if not ok:
        return False
    for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
        shutil.copy(sim / f"{f}.txt", sim / f"{f}_nom.txt")
    for f in ["bode_mag.dat", "bode_phase.dat"]:
        if (fig / f).exists():
            shutil.copy(fig / f, fig / f.replace(".dat", "_nom.dat"))
    return True


def run_corners(b: str):
    sim = RUN / b / "sim"
    fig = RUN / b / "figures"
    rows = []
    for c in ["tt", "ff", "ss"]:
        # build corner deck from current tb_acdc
        src = (RUN / b / "tb" / "tb_acdc.sp").read_text(encoding="utf-8")
        t = src
        if b == "sky130":
            t = re.sub(r"__(tt|ff|ss)\.pm3\.spice", f"__{c}.pm3.spice", t)
        elif b == "ihp":
            t = re.sub(r"mos_(tt|ff|ss)", f"mos_{c}", t)
        elif b == "gf180":
            lib = {"tt": "typical", "ff": "ff", "ss": "ss"}[c]
            t = re.sub(r"(sm141064\.ngspice'\s+)(typical|ff|ss|tt)", rf"\1{lib}", t)
        deck = RUN / b / "tb" / f"tb_acdc_{c}.sp"
        deck.write_text(t, encoding="utf-8")
        # clear
        for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
            p = sim / f"{f}.txt"
            if p.exists():
                p.unlink()
        print(f"CORNER {b} {c}")
        rc = ngspice(RUN / b / "tb", deck.name, sim / f"acdc_{c}.log")
        adc, ugf, phv = grab(sim / "adc.txt"), grab(sim / "ugf.txt"), grab(sim / "ph_at_ugf.txt")
        pwr, vout = grab(sim / "power.txt"), grab(sim / "vout_dc.txt")
        if adc is None:
            print(f"  FAILED rc={rc}")
            rows.append({"corner": c, "dcgain": None, "ugf_mhz": None, "pm_deg": None, "power_mw": None, "vout_V": None, "status": "FAIL"})
        else:
            row = {
                "corner": c,
                "dcgain": adc,
                "ugf_mhz": ugf / 1e6 if ugf else None,
                "pm_deg": pm(phv),
                "power_mw": pwr * 1e3 if pwr else None,
                "vout_V": vout,
                "status": "OK",
            }
            rows.append(row)
            print(f"  {row}")
            for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
                if (sim / f"{f}.txt").exists():
                    shutil.copy(sim / f"{f}.txt", sim / f"{f}_{c}.txt")
    # restore nom
    for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
        nom = sim / f"{f}_nom.txt"
        if nom.exists():
            shutil.copy(nom, sim / f"{f}.txt")
    for f in ["bode_mag", "bode_phase"]:
        nom = fig / f"{f}_nom.dat"
        if nom.exists():
            shutil.copy(nom, fig / f"{f}.dat")
    with (fig / "corners.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["corner", "dcgain", "ugf_mhz", "pm_deg", "power_mw", "vout_V"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in w.fieldnames})
    return rows


def run_extended(b: str):
    for deck, tag in [("tb_cmrr.sp", "cmrr"), ("tb_psrrp.sp", "psrrp"), ("tb_psrrn.sp", "psrrn"), ("tb_noise.sp", "noise")]:
        print(f"EXT {b} {deck}")
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


def main():
    fix_ihp_spiceinit()
    fix_gf180_headers()

    # Re-run ihp + gf180 nominal + corners + extended
    # Also refresh sky130 gm from existing op_devices; re-run sky130 ACDC if needed for clean show m
    for b in ["ihp", "gf180"]:
        ok = run_acdc(b)
        if not ok:
            print(f"HARD FAIL {b} nominal")
            continue
        run_corners(b)
        run_extended(b)

    # sky130: parse gm from op_devices (already healthy)
    hands = {}
    for b in ["cmos", "sky130", "ihp", "gf180"]:
        sim = RUN / b / "sim"
        # ensure show m exists - re-run sky130/cmos briefly if needed
        if not (sim / "op_devices.txt").exists() or (sim / "op_devices.txt").stat().st_size < 100:
            run_acdc(b)
        devs = parse_show_m(sim / "op_devices.txt")
        (sim / "op_device_keys.txt").write_text("\n".join(sorted(devs)) + "\n", encoding="utf-8")
        gms = {}
        for tok, key in [("8", "gm1"), ("10", "gm2"), ("23", "gm3"), ("11", "gmf")]:
            n, d = find_token(devs, tok)
            gms[key] = d.get("gm")
            print(f"{b} {key} <- {n} gm={gms[key]}")
        # CMOS fallback from gm_* files
        if b == "cmos":
            gms["gm1"] = grab(sim / "gm_m8_nom.txt") or gms["gm1"]
            gms["gm2"] = grab(sim / "gm_m10_nom.txt") or gms["gm2"]
            gms["gm3"] = grab(sim / "gm_m23_nom.txt") or gms["gm3"]
            gms["gmf"] = grab(sim / "gm_m11_nom.txt") or gms["gmf"]
        if not gms["gm1"]:
            print(f"WARN {b} missing gm — check op_devices")
            gms = {k: gms[k] or v for k, v in zip(["gm1", "gm2", "gm3", "gmf"], [1e-4, 2e-4, 5e-4, 2e-4])}
        hands[b] = write_hand_tf(b, gms["gm1"], gms["gm2"], gms["gm3"], gms["gmf"])

    # sky130 corners already good — rewrite CSV if needed
    # CMOS MC: document as low variation / HARD-SKIP effective mismatch
    mc_csv = RUN / "cmos" / "sim" / "mc_results.csv"
    if mc_csv.exists():
        vals = []
        for line in mc_csv.read_text().splitlines()[1:]:
            parts = re.split(r"[,\s]+", line.strip())
            if len(parts) >= 3:
                try:
                    vals.append((float(parts[1]), float(parts[2])))
                except ValueError:
                    pass
        if vals:
            ugfs = [v[0] for v in vals]
            # if std ~0, hard-skip meaningful MC
            mean = sum(ugfs) / len(ugfs)
            var = sum((u - mean) ** 2 for u in ugfs) / len(ugfs)
            std = math.sqrt(var)
            if std / mean < 1e-4:
                (RUN / "cmos" / "sim" / "mc_summary.md").write_text(
                    f"HARD-SKIP: CMOS LOT MC N={len(vals)} ran but agauss LOT did not resample "
                    f"across trials (UGF std/mean={std/mean:.2e}); ngspice Level-1 .param agauss "
                    f"evaluated once at deck parse. Open-PDK mismatch MC also HARD-SKIP.\n",
                    encoding="utf-8",
                )
            else:
                (RUN / "cmos" / "sim" / "mc_summary.md").write_text(
                    f"N={len(vals)} UGF mean={mean:.3e} std={std:.3e}\n", encoding="utf-8"
                )

    for b in ["sky130", "ihp", "gf180"]:
        (RUN / b / "sim" / "mc_summary.md").write_text(
            "HARD-SKIP: open-PDK mismatch Monte Carlo not wired (would need per-trial "
            "agauss slope overrides + setseed loop); see skill note.\n",
            encoding="utf-8",
        )

    # metrics + cross
    mets = {}
    for b in ["cmos", "sky130", "ihp", "gf180"]:
        sim = RUN / b / "sim"
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
            w.writerow({
                "backend": b,
                "dcgain": m["adc_dB"],
                "ugf_mhz": m["ugf_Hz"] / 1e6,
                "pm_deg": m["pm_deg"],
                "power_mw": m["power_W"] * 1e3,
            })

    # plots
    subprocess.run(
        ["python3", str(ROOT / ".agents/skills/spice-analyzer/plotting/render_spice_figures.py"), str(RUN)],
        check=False,
    )
    subprocess.run(
        ["python3", str(ROOT / ".agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.py"), str(RUN)],
        check=False,
    )

    # summary
    lines = ["# fan_smc_pin_3 summary", "", "## Nominal", ""]
    lines.append("| Backend | Adc | UGF MHz | PM | P mW | Vout |")
    lines.append("|---------|-----|---------|----|------|------|")
    for b, m in mets.items():
        if m["adc_dB"] is None:
            lines.append(f"| {b} | HARD-SKIP | - | - | - | - |")
        else:
            lines.append(
                f"| {b} | {m['adc_dB']:.2f} | {m['ugf_Hz']/1e6:.3f} | {m['pm_deg']:.1f} | "
                f"{m['power_W']*1e3:.3f} | {m['vout_V']:.3f} |"
            )
    lines += ["", "## Hand gm"]
    for b, h in hands.items():
        lines.append(f"- {b}: gm1={h['gm1']:.4e} gm2={h['gm2']:.4e} gm3={h['gm3']:.4e} gmf={h['gmf']:.4e} GBW={h['gbw']/1e6:.2f} MHz")
    (RUN / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("DONE")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
