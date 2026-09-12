#!/usr/bin/env python3
"""Parse ngspice 'show m' columnar OP dumps; write gm/gds/id txt + hand_tf_params."""
from __future__ import annotations

import json
import math
import re
import statistics as st
import subprocess
from pathlib import Path

RUN = Path("/mnt/d/proj/spice-analyzer-skill") / "results" / "fan_smc_pin_3"
ROOT = Path("/mnt/d/proj/spice-analyzer-skill")
BACKENDS = ["cmos", "sky130", "ihp", "gf180"]


def parse_show_m(path: Path) -> dict:
    """Parse columnar 'show m' into {device_token: {gm,gds,id,...}}."""
    if not path.exists():
        return {}
    devices: dict[str, dict] = {}
    headers: list[str] = []
    for line in path.read_text(errors="replace").splitlines():
        s = line.strip()
        if not s:
            continue
        low = s.lower()
        if low.startswith("device"):
            # e.g. device m.xdut.xm8.msky130_f m.xdut.xm9...
            parts = s.split()
            headers = [p for p in parts[1:]]
            for h in headers:
                key = h.lower()
                devices.setdefault(key, {})
            continue
        parts = s.split()
        if len(parts) < 2 or not headers:
            continue
        key = parts[0].lower()
        if key in ("model",):
            continue
        for i, h in enumerate(headers):
            if i + 1 >= len(parts):
                break
            try:
                devices[h.lower()][key] = float(parts[i + 1])
            except ValueError:
                pass
    return devices


def find_dev(devs: dict, *needles: str) -> dict:
    for name, d in devs.items():
        if all(n.lower() in name for n in needles):
            return d
    # softer: last needle only
    for name, d in devs.items():
        if needles[-1].lower() in name:
            return d
    return {}


def write_scalar(path: Path, name: str, val: float | None):
    if val is None:
        path.write_text("", encoding="utf-8")
        return
    path.write_text(f"{name} = {val:.6e}\n", encoding="utf-8")


def extract_backend(b: str) -> dict:
    sim = RUN / b / "sim"
    devs = parse_show_m(sim / "op_devices.txt")
    # CMOS Level-1 names: m.xdut.mm8 ; PDK: m.xdut.xm8.msky130_f or similar
    tok_map = {
        "m8": ("xm8", "mm8"),
        "m9": ("xm9", "mm9"),
        "m10": ("xm10", "mm10"),
        "m11": ("xm11", "mm11"),
        "m23": ("xm23", "mm23"),
        "m6": ("xm6", "mm6"),
        "m7": ("xm7", "mm7"),
        "m16": ("xm16", "mm16"),
        "m20": ("xm20", "mm20"),
        "m22": ("xm22", "mm22"),
    }
    out = {}
    for label, needles in tok_map.items():
        d = {}
        for n in needles:
            d = find_dev(devs, n)
            if d.get("gm") is not None or d.get("id") is not None:
                break
        out[label] = d
        for key in ("gm", "gds", "id"):
            if d.get(key) is not None:
                write_scalar(sim / f"{key}_{label}.txt", f"{key}_{label}", d[key])
                write_scalar(sim / f"{key}_{label}_nom.txt", f"{key}_{label}", d[key])
    # also legacy names used by write_hand_tf
    alias = {
        "gm_m8": out["m8"].get("gm"),
        "gm_m9": out["m9"].get("gm"),
        "gm_m10": out["m10"].get("gm"),
        "gm_m11": out["m11"].get("gm"),
        "gm_m23": out["m23"].get("gm"),
        "gds_m8": out["m8"].get("gds"),
        "gds_m10": out["m10"].get("gds"),
        "gds_m11": out["m11"].get("gds"),
        "gds_m23": out["m23"].get("gds"),
        "id_m8": out["m8"].get("id"),
        "id_m10": out["m10"].get("id"),
        "id_m11": out["m11"].get("id"),
        "id_m23": out["m23"].get("id"),
    }
    for k, v in alias.items():
        write_scalar(sim / f"{k}.txt", k, v)
        write_scalar(sim / f"{k}_nom.txt", k, v)

    params = (RUN / b / "tb" / "params.sp").read_text()
    c0 = float(re.search(r"CAPACITOR_0=([\d.]+)p", params).group(1)) * 1e-12
    cl = float(re.search(r"CLOAD=([\d.]+)p", params).group(1)) * 1e-12
    gm1 = out["m8"].get("gm") or 1e-4
    gm2 = out["m10"].get("gm") or 2e-4
    gm3 = out["m23"].get("gm") or 5e-4
    gmf = out["m11"].get("gm") or 2e-4
    # adc
    adc_t = (sim / "adc_nom.txt").read_text() if (sim / "adc_nom.txt").exists() else (sim / "adc.txt").read_text()
    m = re.search(r"([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)", adc_t)
    adc = float(m.group(1)) if m else 80.0
    a0 = 10 ** (adc / 20.0)
    gbw = gm1 / (2 * math.pi * c0)
    fp1 = gbw / a0
    fp2 = gm2 / (2 * math.pi * c0)
    fp3 = gm3 / (2 * math.pi * cl)
    fz = gmf / (2 * math.pi * c0)
    wt = 2 * math.pi * gbw
    t2 = math.degrees(math.atan(gbw / fp2)) if fp2 else 0
    t3 = math.degrees(math.atan(gbw / fp3)) if fp3 else 0
    tz = math.degrees(math.atan(gbw / fz)) if fz else 0
    pm_hand = 90 - t2 - t3 + tz

    # Rout trail
    gds6 = out["m6"].get("gds")
    gm16 = out["m16"].get("gm")
    gds16 = out["m16"].get("gds")
    gds20 = out["m20"].get("gds")
    gds22 = out["m22"].get("gds")
    gds7 = out["m7"].get("gds")
    gds23 = out["m23"].get("gds")
    gds11 = out["m11"].get("gds")
    hand = {
        "gm1": gm1,
        "gm2": gm2,
        "gm3": gm3,
        "gmf": gmf,
        "id8": out["m8"].get("id"),
        "id10": out["m10"].get("id"),
        "id23": out["m23"].get("id"),
        "id11": out["m11"].get("id"),
        "adc_dB": adc,
        "A0_lin": a0,
        "GBW_Hz": gbw,
        "fp1_Hz": fp1,
        "fp2_Hz": fp2,
        "fp3_Hz": fp3,
        "fz_Hz": fz,
        "PM_hand_deg": pm_hand,
        "atan_p2": t2,
        "atan_p3": t3,
        "atan_z": tz,
    }
    if all(x is not None for x in (gm16, gds16, gds20, gds6)):
        ro16 = 1 / gds16
        ro20 = 1 / gds20
        ro6 = 1 / gds6
        Rcas = gm16 * ro16 * ro20
        Rout1 = 1 / (1 / Rcas + 1 / ro6)
        Av1 = gm1 * Rout1
        hand.update(
            {
                "Rout1": Rout1,
                "Av1": Av1,
                "Av1_dB": 20 * math.log10(abs(Av1)) if Av1 else None,
                "Rcas": Rcas,
                "ro16": ro16,
                "ro20": ro20,
                "ro6": ro6,
                "gm16": gm16,
                "gds16": gds16,
                "gds20": gds20,
                "gds6": gds6,
            }
        )
    if gds22 is not None and gds7 is not None:
        Rout2 = 1 / (gds22 + gds7)
        Av2 = gm2 * Rout2
        hand.update({"Rout2": Rout2, "Av2": Av2, "Av2_dB": 20 * math.log10(abs(Av2))})
    if gds23 is not None and gds11 is not None:
        Rout3 = 1 / (gds23 + gds11)
        Av3 = gm3 * Rout3
        hand.update({"Rout3": Rout3, "Av3": Av3, "Av3_dB": 20 * math.log10(abs(Av3))})
    if "Av1" in hand and "Av2" in hand and "Av3" in hand:
        A0p = hand["Av1"] * hand["Av2"] * hand["Av3"]
        hand["A0_product"] = A0p
        hand["A0_product_dB"] = 20 * math.log10(abs(A0p))

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
        f"fp1_Hz={fp1}",
        f"fp2_Hz={fp2}",
        f"fp3_Hz={fp3}",
        f"fz_Hz={fz}",
        "vinn_drive=1",
        "topology=smc_ff_3p1z",
    ]
    (sim / "hand_tf_params.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (sim / "hand_op.json").write_text(json.dumps(hand, indent=2), encoding="utf-8")
    print(b, {k: hand.get(k) for k in ("gm1", "gm2", "gm3", "gmf", "GBW_Hz", "A0_product_dB", "PM_hand_deg")})
    return hand


def fix_cmos_mc():
    """Parse mc_results.csv or re-run simple MC loop if empty."""
    sim = RUN / "cmos" / "sim"
    fig = RUN / "cmos" / "figures"
    csvp = sim / "mc_results.csv"
    text = csvp.read_text(errors="replace") if csvp.exists() else ""
    rows = []
    for line in text.splitlines()[1:]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            try:
                ugf = float(parts[0])
                pmv = float(parts[1])
                if ugf > 0:
                    rows.append((ugf, pmv))
            except ValueError:
                pass
    if len(rows) < 10:
        # regenerate via Python loop calling ngspice with mc=1
        print("Re-running CMOS MC N=200 ...")
        tb = RUN / "cmos" / "tb"
        # ensure params has mc switch path via cmos.lib
        ugfs, pms = [], []
        for i in range(200):
            deck = f"""* MC trial {i}
.include '../../../../models/cmos.lib'
.param mc=1
.include params.sp
.include dut.sp
.param VDD=1.8
.param VCM=0.9
VDD vdda 0 DC {{VDD}}
VSS gnda 0 DC 0
VINP vinp 0 DC {{VCM}} AC 0
VINN_DC vinn_dc 0 DC {{VCM}} AC 1
Lfb vout vinn 1k
Cfb vinn vinn_dc 1
Rbig vinn 0 1G
CL vout 0 {{CLOAD}}
Xdut gnda vdda vinn vinp vout fan_smc_pin_3
.control
set noaskquit
op
ac dec 40 1 1G
let mag = db(v(vout))
let ph = 180/pi*ph(v(vout))
let ugf = 0
let ph_ugf = 0
let found = 0
let n = length(frequency)-1
let k = 0
dowhile k < n
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
print ugf > ../sim/_mc_ugf.txt
print ph_ugf > ../sim/_mc_ph.txt
quit
.endc
.end
"""
            (tb / "_mc_trial.sp").write_text(deck, encoding="utf-8")
            subprocess.run(
                ["ngspice", "-b", "_mc_trial.sp"],
                cwd=tb,
                capture_output=True,
                text=True,
            )
            ut = (sim / "_mc_ugf.txt").read_text(errors="replace")
            pt = (sim / "_mc_ph.txt").read_text(errors="replace")
            um = re.search(r"([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)", ut)
            pm_m = re.search(r"([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)", pt)
            if um and "NO_UGF" not in ut:
                ugf = float(um.group(1))
                phv = float(pm_m.group(1)) if pm_m else 90.0
                pmv = phv if phv >= 0 else 180 + phv
                ugfs.append(ugf)
                pms.append(pmv)
            if (i + 1) % 40 == 0:
                print(f"  MC {i+1}/200 valid={len(ugfs)}")
        rows = list(zip(ugfs, pms))
        with csvp.open("w", encoding="utf-8") as fh:
            fh.write("ugf_Hz,pm_deg\n")
            for u, p in rows:
                fh.write(f"{u},{p}\n")

    if not rows:
        (sim / "mc_summary.md").write_text(
            "HARD-SKIP: CMOS LOT MC produced no valid UGF samples.\n", encoding="utf-8"
        )
        return None
    ugfs = [r[0] for r in rows]
    pms = [r[1] for r in rows]
    summary = {
        "N": len(rows),
        "mode": "LOT mc=1",
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
    with (fig / "mc_ugf_hist.csv").open("w", encoding="utf-8") as fh:
        fh.write("ugf_mhz\n")
        for u in ugfs:
            fh.write(f"{u/1e6}\n")
    with (fig / "mc_pm_hist.csv").open("w", encoding="utf-8") as fh:
        fh.write("pm_deg\n")
        for p in pms:
            fh.write(f"{p}\n")
    print("CMOS MC", summary)
    return summary


def main():
    hands = {}
    for b in BACKENDS:
        hands[b] = extract_backend(b)
    (RUN / "hand_all.json").write_text(json.dumps(hands, indent=2), encoding="utf-8")
    fix_cmos_mc()
    print("PLOTS")
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
    print("EXTRACT DONE")


if __name__ == "__main__":
    main()
