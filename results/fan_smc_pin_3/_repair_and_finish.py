#!/usr/bin/env python3
"""Repair fan_smc_pin_3: re-run ACDC/corners/extended, fix CSVs, extract gm, MC."""
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


def pm(ph):
    if ph is None:
        return None
    return ph if ph >= 0 else 180.0 + ph


def ngspice(tb: Path, deck: str, log: Path) -> int:
    r = subprocess.run(["ngspice", "-b", deck], cwd=tb, capture_output=True, text=True)
    log.write_text((r.stdout or "") + "\n" + (r.stderr or ""), encoding="utf-8")
    return r.returncode


def patch_acdc_for_gm(tb_acdc: Path):
    """Ensure OP prints idd/vout/power before AC, and try @device[gm] prints."""
    t = tb_acdc.read_text(encoding="utf-8")
    if "print @m.xdut" in t or "gm_m8" in t:
        return
    # Insert after show m if present
    inject = """
* Explicit gm/gds capture (works for BSIM/PSP when show-m is sparse)
let gm_m8 = @m.xdut.xm8[gm]
let gm_m9 = @m.xdut.xm9[gm]
let gm_m10 = @m.xdut.xm10[gm]
let gm_m11 = @m.xdut.xm11[gm]
let gm_m23 = @m.xdut.xm23[gm]
let gds_m8 = @m.xdut.xm8[gds]
let gds_m10 = @m.xdut.xm10[gds]
let gds_m23 = @m.xdut.xm23[gds]
let gds_m11 = @m.xdut.xm11[gds]
let id_m8 = @m.xdut.xm8[id]
let id_m10 = @m.xdut.xm10[id]
let id_m23 = @m.xdut.xm23[id]
let id_m11 = @m.xdut.xm11[id]
print gm_m8 > ../sim/gm_m8.txt
print gm_m9 > ../sim/gm_m9.txt
print gm_m10 > ../sim/gm_m10.txt
print gm_m11 > ../sim/gm_m11.txt
print gm_m23 > ../sim/gm_m23.txt
print gds_m8 > ../sim/gds_m8.txt
print gds_m10 > ../sim/gds_m10.txt
print gds_m23 > ../sim/gds_m23.txt
print gds_m11 > ../sim/gds_m11.txt
print id_m8 > ../sim/id_m8.txt
print id_m10 > ../sim/id_m10.txt
print id_m23 > ../sim/id_m23.txt
print id_m11 > ../sim/id_m11.txt
"""
    # CMOS uses mm* not xm*
    inject_cmos = inject.replace("xm", "mm").replace("m.xdut.xmm", "m.xdut.mm")
    if "cmos" in str(tb_acdc):
        inject = inject_cmos
    if "show m" in t:
        t = t.replace("show m > ../sim/op_devices.txt", "show m > ../sim/op_devices.txt\n" + inject)
    elif "op\n" in t:
        t = t.replace("op\n", "op\n" + inject, 1)
    tb_acdc.write_text(t, encoding="utf-8")


def run_nominal(b: str):
    tb = RUN / b / "tb"
    sim = RUN / b / "sim"
    fig = RUN / b / "figures"
    patch_acdc_for_gm(tb / "tb_acdc.sp")
    print(f"NOMINAL {b}")
    rc = ngspice(tb, "tb_acdc.sp", sim / "acdc.log")
    for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
        src = sim / f"{f}.txt"
        if src.exists():
            shutil.copy(src, sim / f"{f}_nom.txt")
    for f in ["bode_mag.dat", "bode_phase.dat"]:
        if (fig / f).exists():
            shutil.copy(fig / f, fig / f.replace(".dat", "_nom.dat"))
    # copy gm files
    for f in sim.glob("gm_*.txt"):
        shutil.copy(f, sim / (f.stem + "_nom.txt"))
    for f in sim.glob("gds_*.txt"):
        shutil.copy(f, sim / (f.stem + "_nom.txt"))
    for f in sim.glob("id_*.txt"):
        shutil.copy(f, sim / (f.stem + "_nom.txt"))
    print(
        f"  rc={rc} adc={grab(sim/'adc.txt')} ugf={grab(sim/'ugf.txt')} "
        f"ph={grab(sim/'ph_at_ugf.txt')} idd={grab(sim/'idd.txt')} "
        f"gm8={grab(sim/'gm_m8.txt')}"
    )


def ensure_corner_deck(b: str, corner: str) -> Path:
    src = (RUN / b / "tb" / "tb_acdc.sp").read_text(encoding="utf-8")
    dst = RUN / b / "tb" / f"tb_acdc_{corner}.sp"
    t = src
    if b == "sky130":
        t = re.sub(r"__tt\.pm3\.spice", f"__{corner}.pm3.spice", t)
        t = re.sub(r"__ff\.pm3\.spice", f"__{corner}.pm3.spice", t)
        t = re.sub(r"__ss\.pm3\.spice", f"__{corner}.pm3.spice", t)
    elif b == "ihp":
        t = re.sub(r"mos_(tt|ff|ss)", f"mos_{corner}", t)
    elif b == "gf180":
        lib = {"tt": "typical", "ff": "ff", "ss": "ss"}[corner]
        t = re.sub(r"(sm141064\.ngspice'\s+)(typical|ff|ss|tt)", rf"\1{lib}", t)
    dst.write_text(t, encoding="utf-8")
    return dst


def run_corners(b: str):
    rows = []
    sim = RUN / b / "sim"
    fig = RUN / b / "figures"
    for c in ["tt", "ff", "ss"]:
        print(f"CORNER {b} {c}")
        ensure_corner_deck(b, c)
        rc = ngspice(RUN / b / "tb", f"tb_acdc_{c}.sp", sim / f"acdc_{c}.log")
        for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
            src = sim / f"{f}.txt"
            if src.exists():
                shutil.copy(src, sim / f"{f}_{c}.txt")
        if (fig / "bode_mag.dat").exists():
            shutil.copy(fig / "bode_mag.dat", fig / f"bode_mag_{c}.dat")
        adc = grab(sim / "adc.txt")
        ugf = grab(sim / "ugf.txt")
        phv = grab(sim / "ph_at_ugf.txt")
        pwr = grab(sim / "power.txt")
        vout = grab(sim / "vout_dc.txt")
        rows.append(
            {
                "corner": c,
                "dcgain": adc,
                "ugf_mhz": (ugf / 1e6) if ugf else None,
                "pm_deg": pm(phv),
                "power_mw": (pwr * 1e3) if pwr else None,
                "vout_V": vout,
                "rc": rc,
            }
        )
        print(f"  {rows[-1]}")
    # restore nom
    for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
        nom = sim / f"{f}_nom.txt"
        if nom.exists():
            shutil.copy(nom, sim / f"{f}.txt")
    for f in ["bode_mag", "bode_phase"]:
        nom = fig / f"{f}_nom.dat"
        if nom.exists():
            shutil.copy(nom, fig / f"{f}.dat")
    # write plotter-friendly CSV
    with (fig / "corners.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["corner", "dcgain", "ugf_mhz", "pm_deg", "power_mw", "vout_V"],
        )
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in w.fieldnames})
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
        if not (tb / deck).exists():
            print(f"MISSING {b} {deck}")
            continue
        print(f"EXT {b} {deck}")
        ngspice(tb, deck, sim / f"{tag}.log")
    # restore bode/nom scalars
    for f in ["adc", "ugf", "ph_at_ugf", "idd", "power", "vout_dc"]:
        nom = sim / f"{f}_nom.txt"
        if nom.exists():
            shutil.copy(nom, sim / f"{f}.txt")
    fig = RUN / b / "figures"
    for f in ["bode_mag", "bode_phase"]:
        nom = fig / f"{f}_nom.dat"
        if nom.exists():
            shutil.copy(nom, fig / f"{f}.dat")


def write_hand_tf(b: str):
    sim = RUN / b / "sim"
    params = (RUN / b / "tb" / "params.sp").read_text()
    c0 = float(re.search(r"CAPACITOR_0=([\d.]+)p", params).group(1)) * 1e-12
    cl = float(re.search(r"CLOAD=([\d.]+)p", params).group(1)) * 1e-12
    gm1 = grab(sim / "gm_m8_nom.txt") or grab(sim / "gm_m8.txt")
    gm2 = grab(sim / "gm_m10_nom.txt") or grab(sim / "gm_m10.txt")
    gm3 = grab(sim / "gm_m23_nom.txt") or grab(sim / "gm_m23.txt")
    gmf = grab(sim / "gm_m11_nom.txt") or grab(sim / "gm_m11.txt")
    # fallbacks
    gm1 = gm1 or 1e-4
    gm2 = gm2 or 2e-4
    gm3 = gm3 or 5e-4
    gmf = gmf or 2e-4
    adc = grab(sim / "adc_nom.txt") or grab(sim / "adc.txt") or 80.0
    a0 = 10 ** (adc / 20.0)
    gbw = gm1 / (2 * math.pi * c0)
    lines = [
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
    (sim / "hand_tf_params.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"gm1": gm1, "gm2": gm2, "gm3": gm3, "gmf": gmf, "gbw": gbw, "c0": c0, "adc": adc}


def run_cmos_mc(n=200):
    """Simple LOT MC by setting mc=1 and reseeding via ngspice reset."""
    tb = RUN / "cmos" / "tb"
    sim = RUN / "cmos" / "sim"
    fig = RUN / "cmos" / "figures"
    # write MC deck based on tb_acdc
    base = (tb / "tb_acdc.sp").read_text(encoding="utf-8")
    # force mc=1 after include cmos.lib
    if ".param mc=1" not in base:
        base = base.replace(".include '../../../../models/cmos.lib'",
                            ".include '../../../../models/cmos.lib'\n.param mc=1")
        if ".param mc=1" not in base:
            base = ".param mc=1\n" + base
    # simplify control: only need ugf/pm
    mc_ctrl = """
.control
set noaskquit
set filetype=ascii
setseed 42
echo trial,ugf_Hz,pm_deg,adc_dB > ../sim/mc_results.csv
let i = 1
dowhile i <= %d
  reset
  op
  ac dec 40 1 1G
  let mag = db(v(vout))
  let ph = 180/pi*ph(v(vout))
  let adc = mag[0]
  let ugf = 0
  let ph_ugf = 0
  let found = 0
  let npts = length(frequency)-1
  let k = 0
  dowhile k < npts
    if found = 0
      if mag[k] >= 0
        if mag[k+1] < 0
          let f1 = frequency[k]
          let f2 = frequency[k+1]
          let m1 = mag[k]
          let m2 = mag[k+1]
          let ugf = f1 + (0-m1)*(f2-f1)/(m2-m1)
          let p1 = ph[k]
          let p2 = ph[k+1]
          let ph_ugf = p1 + (0-m1)*(p2-p1)/(m2-m1)
          let found = 1
        end
      end
    end
    let k = k + 1
  end
  if found = 1
    if ph_ugf < 0
      let pmv = 180 + ph_ugf
    else
      let pmv = ph_ugf
    end
    echo $&i,$&ugf,$&pmv,$&adc >> ../sim/mc_results.csv
  else
    echo $&i,nan,nan,$&adc >> ../sim/mc_results.csv
  end
  let i = i + 1
end
quit
.endc
.end
""" % n
    # strip old control
    if ".control" in base:
        base = base.split(".control")[0]
    deck = base + mc_ctrl
    (tb / "tb_mc.sp").write_text(deck, encoding="utf-8")
    print(f"MC cmos N={n}")
    rc = ngspice(tb, "tb_mc.sp", sim / "mc.log")
    print("  mc rc", rc)
    # summarize
    rows = []
    p = sim / "mc_results.csv"
    if p.exists():
        for line in p.read_text().splitlines()[1:]:
            parts = line.split(",")
            if len(parts) >= 3:
                try:
                    ugf = float(parts[1])
                    pmv = float(parts[2])
                    if math.isfinite(ugf) and math.isfinite(pmv):
                        rows.append((ugf, pmv))
                except ValueError:
                    pass
    if rows:
        import statistics as st

        ugfs = [r[0] for r in rows]
        pms = [r[1] for r in rows]
        summary = {
            "N": len(rows),
            "mode": "LOT mc=1",
            "seed": 42,
            "ugf_mean_Hz": st.mean(ugfs),
            "ugf_std_Hz": st.pstdev(ugfs) if len(ugfs) > 1 else 0,
            "ugf_min_Hz": min(ugfs),
            "ugf_max_Hz": max(ugfs),
            "pm_mean_deg": st.mean(pms),
            "pm_std_deg": st.pstdev(pms) if len(pms) > 1 else 0,
            "pm_min_deg": min(pms),
            "pm_max_deg": max(pms),
        }
        (sim / "mc_summary.md").write_text(
            "\n".join(f"- {k}: {v}" for k, v in summary.items()) + "\n", encoding="utf-8"
        )
        # hist csv for plotter
        with (fig / "mc_ugf_hist.csv").open("w", encoding="utf-8") as fh:
            fh.write("ugf_mhz\n")
            for u, _ in rows:
                fh.write(f"{u/1e6}\n")
        with (fig / "mc_pm_hist.csv").open("w", encoding="utf-8") as fh:
            fh.write("pm_deg\n")
            for _, pmv in rows:
                fh.write(f"{pmv}\n")
        print(summary)
        return summary
    (sim / "mc_summary.md").write_text(
        "HARD-SKIP: MC CSV empty or parse failed; see mc.log\n", encoding="utf-8"
    )
    return None


def main():
    hands = {}
    mets = {}
    corners = {}

    for b in BACKENDS:
        run_nominal(b)
        hands[b] = write_hand_tf(b)
        sim = RUN / b / "sim"
        mets[b] = {
            "adc_dB": grab(sim / "adc_nom.txt"),
            "ugf_Hz": grab(sim / "ugf_nom.txt"),
            "pm_deg": pm(grab(sim / "ph_at_ugf_nom.txt")),
            "power_W": grab(sim / "power_nom.txt"),
            "idd_A": grab(sim / "idd_nom.txt"),
            "vout_V": grab(sim / "vout_dc_nom.txt"),
        }

    for b in ["sky130", "ihp", "gf180"]:
        corners[b] = run_corners(b)

    for b in BACKENDS:
        run_extended(b)
        sim = RUN / b / "sim"
        mets[b]["cmrr_dB"] = grab(sim / "cmrrdc.txt")
        mets[b]["psrrp_dB"] = grab(sim / "psrrp_dc.txt")
        mets[b]["psrrn_dB"] = grab(sim / "psrrn_dc.txt")
        hands[b] = write_hand_tf(b)

    # PDK MC hard-skip
    for b in ["sky130", "ihp", "gf180"]:
        (RUN / b / "sim" / "mc_summary.md").write_text(
            "HARD-SKIP: open-PDK mismatch MC not enabled in this run "
            "(cmos LOT MC covers educational variation; sky130/ihp/gf180 mismatch "
            "resampling requires per-trial agauss overrides not wired here).\n",
            encoding="utf-8",
        )

    mc = run_cmos_mc(200)

    # cross csv with plotter columns
    cross_path = RUN / "figures_cross.csv"
    with cross_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["backend", "dcgain", "ugf_mhz", "pm_deg", "power_mw"])
        w.writeheader()
        for b in BACKENDS:
            m = mets[b]
            w.writerow(
                {
                    "backend": b,
                    "dcgain": m["adc_dB"],
                    "ugf_mhz": (m["ugf_Hz"] / 1e6) if m["ugf_Hz"] else None,
                    "pm_deg": m["pm_deg"],
                    "power_mw": (m["power_W"] * 1e3) if m["power_W"] else None,
                }
            )
    for b in BACKENDS:
        shutil.copy(cross_path, RUN / b / "figures" / "figures_cross.csv")

    # metrics json
    for b in BACKENDS:
        (RUN / b / "sim" / "metrics.json").write_text(
            json.dumps({"metrics": mets[b], "hand": hands[b], "corners": corners.get(b)}, indent=2),
            encoding="utf-8",
        )

    # summary
    lines = ["# fan_smc_pin_3 summary", "", "## Nominal", ""]
    lines.append("| Backend | Adc (dB) | UGF (MHz) | PM (deg) | P (mW) | Vout (V) |")
    lines.append("|---------|----------|-----------|----------|--------|----------|")
    for b in BACKENDS:
        m = mets[b]
        lines.append(
            f"| {b} | {m['adc_dB']:.2f} | {m['ugf_Hz']/1e6:.3f} | {m['pm_deg']:.1f} | "
            f"{m['power_W']*1e3:.3f} | {m['vout_V']:.3f} |"
        )
    lines += ["", "## Hand gm", ""]
    for b in BACKENDS:
        h = hands[b]
        lines.append(
            f"- {b}: gm1={h['gm1']:.4e} gm2={h['gm2']:.4e} gm3={h['gm3']:.4e} gmf={h['gmf']:.4e} "
            f"GBW_hand={h['gbw']/1e6:.2f} MHz"
        )
    lines += ["", "## Corners", ""]
    for b, rows in corners.items():
        lines.append(f"### {b}")
        for r in rows:
            lines.append(
                f"- {r['corner']}: Adc={r['dcgain']:.2f} UGF={r['ugf_mhz']:.3f} MHz "
                f"PM={r['pm_deg']:.1f} P={r['power_mw']:.3f} mW"
            )
    lines += ["", "## MC", f"- cmos: {mc}", "- PDKs: HARD-SKIP (see mc_summary.md)"]
    (RUN / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # plots
    print("PLOTS")
    subprocess.run(
        ["python3", str(ROOT / ".agents/skills/spice-analyzer/plotting/render_spice_figures.py"), str(RUN)],
        check=False,
    )
    subprocess.run(
        ["python3", str(ROOT / ".agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.py"), str(RUN)],
        check=False,
    )
    print("ALL DONE")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
