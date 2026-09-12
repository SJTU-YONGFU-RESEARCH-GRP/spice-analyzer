#!/usr/bin/env python3
"""Sky130 mismatch MC with external re-parse; keep first N healthy trials."""
from __future__ import annotations

import csv
import json
import random
import re
import statistics
import subprocess
from pathlib import Path

RUN = Path("/mnt/d/proj/spice-analyzer-skill/results/fan_smc_pin_3")
TB = RUN / "sky130" / "tb"
SIM = RUN / "sky130" / "sim"
FIG = RUN / "sky130" / "figures"
NG = "/usr/local/bin/ngspice"
ROOT = "/mnt/d/proj/spice-analyzer-skill"
N_TARGET = 200
MAX_TRIES = 600


def grab(path: Path):
    if not path.exists():
        return None
    t = path.read_text(errors="replace")
    if "NO_UGF" in t:
        return None
    m = re.search(r"=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)", t)
    return float(m.group(1)) if m else None


def one_trial(seed: int) -> tuple[float, float, float] | None:
    random.seed(seed)
    # Mild mismatch slopes (fraction of foundry 1-sigma)
    scale = 0.35
    slopes = {
        "nfet_toxe": random.gauss(0, scale),
        "nfet_vth0": random.gauss(0, scale),
        "nfet_voff": random.gauss(0, scale),
        "pfet_toxe": random.gauss(0, scale),
        "pfet_vth0": random.gauss(0, scale),
        "pfet_voff": random.gauss(0, scale),
    }
    outdir = Path(f"/tmp/fan_sky_mc_{seed}")
    outdir.mkdir(exist_ok=True)
    deck = f"""* sky130 MC trial {seed}
.param VDD=1.8
.param VCM=0.9
.param CL=10p
.temp 27
.option scale=1.0u
.param mc_mm_switch=0
.param mc_pr_switch=0
.param sky130_fd_pr__nfet_01v8__toxe_slope_spectre = {slopes['nfet_toxe']}
.param sky130_fd_pr__nfet_01v8__vth0_slope_spectre = {slopes['nfet_vth0']}
.param sky130_fd_pr__nfet_01v8__voff_slope_spectre = {slopes['nfet_voff']}
.param sky130_fd_pr__pfet_01v8__toxe_slope_spectre = {slopes['pfet_toxe']}
.param sky130_fd_pr__pfet_01v8__vth0_slope_spectre = {slopes['pfet_vth0']}
.param sky130_fd_pr__pfet_01v8__voff_slope_spectre = {slopes['pfet_voff']}
.include '{ROOT}/models/pdk/sky130_fd_pr/models/parameters/lod.spice'
.include '{ROOT}/models/pdk/sky130_fd_pr/cells/nfet_01v8/sky130_fd_pr__nfet_01v8__mismatch.corner.spice'
.include '{ROOT}/models/pdk/sky130_fd_pr/cells/pfet_01v8/sky130_fd_pr__pfet_01v8__mismatch.corner.spice'
.include '{ROOT}/models/pdk/sky130_fd_pr/cells/nfet_01v8/sky130_fd_pr__nfet_01v8__tt.pm3.spice'
.include '{ROOT}/models/pdk/sky130_fd_pr/cells/pfet_01v8/sky130_fd_pr__pfet_01v8__tt.pm3.spice'
.include params.sp
.include dut.sp
VDD vdda 0 DC {{VDD}}
VSS gnda 0 DC 0
VCM vinp 0 DC {{VCM}}
Lfb vout vinn 1e9
Rdummy vinn 0 1e12
Cac vinn vac 1
Vac vac 0 DC 0 AC 1
CL vout 0 {{CL}}
Xdut gnda vdda vinn vinp vout fan_smc_pin_3
.control
set filetype=ascii
op
let vout_op=v(vout)
ac dec 25 1e2 1e9
let mag=vdb(vout)
let ph=vp(vout)*180/pi
let Adc=mag[0]
let ugf=0
let pm=0
let found=0
let k=1
let nn=length(mag)
while k < nn
  if found eq 0
    if mag[k] < 0
      if mag[k-1] >= 0
        let f1=frequency[k-1]
        let f2=frequency[k]
        let m1=mag[k-1]
        let m2=mag[k]
        let ugf=f1+(f2-f1)*m1/(m1-m2)
        let p1=ph[k-1]
        let p2=ph[k]
        let pm=p1+(p2-p1)*(ugf-f1)/(f2-f1)
        let found=1
      end
    end
  end
  let k=k+1
end
print Adc > {outdir}/adc.txt
print ugf > {outdir}/ugf.txt
print pm > {outdir}/pm.txt
print vout_op > {outdir}/vout.txt
quit
.endc
.end
"""
    sp = outdir / "deck.sp"
    sp.write_text(deck)
    subprocess.run([NG, "-b", str(sp)], cwd=str(TB), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    adc = grab(outdir / "adc.txt")
    ugf = grab(outdir / "ugf.txt")
    pm = grab(outdir / "pm.txt")
    vout = grab(outdir / "vout.txt")
    if adc is None or ugf is None or ugf < 1e4 or adc < 40:
        return None
    if vout is None or not (0.3 < vout < 1.5):
        return None
    if pm is not None and -180 <= pm <= 0:
        pm = 180 + pm
    return ugf, float(pm or 0), adc


def main() -> None:
    rows = []
    tries = 0
    seed = 2000
    while len(rows) < N_TARGET and tries < MAX_TRIES:
        tries += 1
        seed += 1
        r = one_trial(seed)
        if r is None:
            continue
        rows.append((len(rows),) + r)
        if len(rows) % 25 == 0:
            print(f"accepted {len(rows)}/{N_TARGET} after {tries} tries; last ugf={r[0]:.3e}")
    out = SIM / "mc_results.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["run", "ugf_Hz", "pm_deg", "Adc_dB"])
        w.writerows(rows)
    ugfs = [r[1] for r in rows]
    pms = [r[2] for r in rows]
    summary = {
        "N": len(rows),
        "tries": tries,
        "mode": "mismatch slopes external re-parse (0.35 sigma); healthy-only",
        "UGF_mean_Hz": statistics.mean(ugfs) if ugfs else None,
        "UGF_std_Hz": statistics.pstdev(ugfs) if len(ugfs) > 1 else 0.0,
        "PM_mean_deg": statistics.mean(pms) if pms else None,
        "PM_std_deg": statistics.pstdev(pms) if len(pms) > 1 else 0.0,
    }
    FIG.mkdir(exist_ok=True)
    (FIG / "mc_ugf_hist.dat").write_text("\n".join(f"{u/1e6:.8e}" for u in ugfs) + "\n")
    (FIG / "mc_pm_hist.dat").write_text("\n".join(f"{p:.8e}" for p in pms) + "\n")
    (SIM / "mc_summary.json").write_text(json.dumps(summary, indent=2))
    (SIM / "mc_summary.md").write_text(
        "\n".join(
            [
                "# MC summary (sky130)",
                "",
                f"- N accepted: {summary['N']} (tries={tries})",
                f"- Mode: {summary['mode']}",
                f"- UGF mean/std Hz: {summary['UGF_mean_Hz']:.4e} / {summary['UGF_std_Hz']:.4e}",
                f"- PM mean/std deg: {summary['PM_mean_deg']:.3f} / {summary['PM_std_deg']:.3f}",
                "",
            ]
        )
    )
    print(summary)


if __name__ == "__main__":
    main()
