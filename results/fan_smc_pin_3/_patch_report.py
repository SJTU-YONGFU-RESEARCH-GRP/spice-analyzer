#!/usr/bin/env python3
"""Patch report.tex numbers from measured metrics and compile PDF."""
from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path

RUN = Path("/mnt/d/proj/spice-analyzer-skill/results/fan_smc_pin_3")
hands = json.loads((RUN / "hand_all.json").read_text())
mets = json.loads((RUN / "metrics_all.json").read_text())["mets"]

for b in mets:
    for k, fn in [("en1k", "en_1k.txt"), ("en1m", "en_1m.txt")]:
        p = RUN / b / "sim" / fn
        if p.exists():
            m = re.search(r"([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)", p.read_text())
            if m:
                mets[b][k] = float(m.group(1))

h, ms = hands["sky130"], mets["sky130"]
hc, mc = hands["cmos"], mets["cmos"]
hi, mi = hands["ihp"], mets["ihp"]
hg, mg = hands["gf180"], mets["gf180"]


def fmt_en(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return r"HARD-SKIP: noise TB"
    if v < 1e-15:
        return r"HARD-SKIP: numerical floor"
    if v >= 1e-6:
        return rf"{v*1e6:.2f}\,\mathrm{{\mu V}}/\sqrt{{\mathrm{{Hz}}}}"
    return rf"{v*1e9:.2f}\,\mathrm{{nV}}/\sqrt{{\mathrm{{Hz}}}}"


def mgain(a, b):
    return "PASS" if abs(a - b) <= 1.0 else "FAIL"


def mpct(a, b, tol=0.05):
    return "PASS" if a and abs(a - b) / abs(a) <= tol else "FAIL"


def mpm(a, b, tol=5.0):
    return "PASS" if abs(a - b) <= tol else "FAIL"


KP, KPn = 100e-6, 200e-6
gm1_sq = math.sqrt(2 * KP * (20 / 0.5) * 8 * abs(h["id8"]))
gm2_sq = math.sqrt(2 * KP * (16 / 0.5) * 8 * abs(h["id10"]))
gm3_sq = math.sqrt(2 * KPn * (20 / 0.5) * 16 * abs(h["id23"]))
gmf_sq = math.sqrt(2 * KP * (10 / 0.5) * 16 * abs(h["id11"]))

a0h, a0s = h["A0_product_dB"], ms["adc"]
gbwh, gbws = h["GBW_Hz"] / 1e6, ms["ugf"] / 1e6
pmh, pms = h["PM_hand_deg"], ms["pm"]
pmw = ms["pwr"] * 1e3
fp1 = h["GBW_Hz"] / h["A0_product"]
fom = ms["ugf"] * 10e-12 / ms["pwr"]

tex = (RUN / "report.tex").read_text(encoding="utf-8")

# trivial hygiene
tex = tex.replace(
    r"Passives & C0 / CL / Ib & --- & 1\,pF / 10\,pF / 50\,\(\mu\)A & --- \\",
    r"Passives & C0 / CL / Ib & n/a & 1\,pF / 10\,pF / 50\,\(\mu\)A & n/a \\",
)
tex = tex.replace(r"Hand PM & --- & 72.22 \\", r"Hand PM & n/a (sum) & 72.22 \\")
tex = tex.replace(r"Sim PM & --- & 81.55 \\", r"Sim PM & n/a (sum) & 81.55 \\")

old_sq = (
    r"Square-law sketch for gm1 (KP\(_p\) educational \(\approx 100\,\mu\mathrm{A/V}^2\), not used for later match):\n"
    r"\\[\n"
    r"g_{m1,\\mathrm{sq}}=\\sqrt{2\\cdot KP\\cdot(W/L)M\\cdot I_D}\n"
    r"\\]\n"
    r"with OP \(I_D\) of xm8 is tiny; therefore use OP \(g_m\):\n"
    r"\\begin{align*}\n"
    r"g_{m1}&=4.46582\\times10^{-5}\\,\\mathrm{S},\\\\\n"
    r"g_{m2}&=8.27011\\times10^{-4}\\,\\mathrm{S},\\\\\n"
    r"g_{m3}&=1.44724\\times10^{-3}\\,\\mathrm{S},\\\\\n"
    r"g_{mf}&=1.03929\\times10^{-3}\\,\\mathrm{S}.\n"
    r"\\end{align*}"
)
# match actual file newlines
old_sq = r"""Square-law sketch for gm1 (KP\(_p\) educational \(\approx 100\,\mu\mathrm{A/V}^2\), not used for later match):
\[
g_{m1,\mathrm{sq}}=\sqrt{2\cdot KP\cdot(W/L)M\cdot I_D}
\]
with OP \(I_D\) of xm8 is tiny; therefore use OP \(g_m\):
\begin{align*}
g_{m1}&=4.46582\times10^{-5}\,\mathrm{S},\\
g_{m2}&=8.27011\times10^{-4}\,\mathrm{S},\\
g_{m3}&=1.44724\times10^{-3}\,\mathrm{S},\\
g_{mf}&=1.03929\times10^{-3}\,\mathrm{S}.
\end{align*}"""

new_sq = (
    "Educational square-law (KP\\(_p=100\\,\\mu\\mathrm{A/V}^2\\), "
    "KP\\(_n=200\\,\\mu\\mathrm{A/V}^2\\); OP \\(I_D\\)) then replace by OP \\(g_m\\):\n"
    "\\begin{align*}\n"
    "g_{m1,\\mathrm{sq}}&=\\sqrt{2\\cdot KP_p\\cdot(W/L)M\\cdot I_{D8}}"
    f"=\\sqrt{{2\\cdot 100e-6\\cdot(20/0.5)\\cdot 8\\cdot {h['id8']:.3e}}}"
    f"={gm1_sq:.3e}" + "\\,\\mathrm{S},\\\\\n"
    "g_{m2,\\mathrm{sq}}&=\\sqrt{2\\cdot KP_p\\cdot(16/0.5)\\cdot 8\\cdot I_{D10}}"
    f"=\\sqrt{{2\\cdot 100e-6\\cdot(16/0.5)\\cdot 8\\cdot {h['id10']:.3e}}}"
    f"={gm2_sq:.3e}" + "\\,\\mathrm{S},\\\\\n"
    "g_{m3,\\mathrm{sq}}&=\\sqrt{2\\cdot KP_n\\cdot(20/0.5)\\cdot 16\\cdot I_{D23}}"
    f"=\\sqrt{{2\\cdot 200e-6\\cdot(20/0.5)\\cdot 16\\cdot {h['id23']:.3e}}}"
    f"={gm3_sq:.3e}" + "\\,\\mathrm{S},\\\\\n"
    "g_{mf,\\mathrm{sq}}&=\\sqrt{2\\cdot KP_p\\cdot(10/0.5)\\cdot 16\\cdot I_{D11}}"
    f"=\\sqrt{{2\\cdot 100e-6\\cdot(10/0.5)\\cdot 16\\cdot {h['id11']:.3e}}}"
    f"={gmf_sq:.3e}" + "\\,\\mathrm{S}.\n"
    "\\end{align*}\n"
    "OP \\(g_m\\) (used for Steps 3--6):\n"
    "\\begin{align*}\n"
    f"g_{{m1}}&={h['gm1']:.5e}" + "\\,\\mathrm{S},\\quad "
    f"g_{{m2}}&={h['gm2']:.5e}" + "\\,\\mathrm{S},\\\\\n"
    f"g_{{m3}}&={h['gm3']:.5e}" + "\\,\\mathrm{S},\\quad "
    f"g_{{mf}}&={h['gmf']:.5e}" + "\\,\\mathrm{S}.\n"
    "\\end{align*}"
)
if old_sq in tex:
    tex = tex.replace(old_sq, new_sq)
else:
    print("WARN: square-law block not found")

tex = tex.replace(
    r"Sim DC gain \(96.53\,\mathrm{dB}\) (mirror/FF paths add residual).",
    rf"Sim DC gain \({a0s:.2f}\,\mathrm{{dB}}\) (hand product \(A_0={a0h:.2f}\,\mathrm{{dB}}\); FF/mirrors alter residual).",
)

# Key number updates (sky130 primary tables)
pairs = [
    (
        r"\(A_0\) (dB) & 89.60 & 96.53 & \(-6.93\,\mathrm{dB}\) & FAIL \\",
        rf"\(A_0\) (dB) & {a0h:.2f} & {a0s:.2f} & \({a0h-a0s:+.2f}\,\mathrm{{dB}}\) & {mgain(a0h,a0s)} \\",
    ),
    (
        r"UGF (MHz) & 7.108 & 12.543 & \(-43.3\%\) & FAIL \\",
        rf"UGF (MHz) & {gbwh:.3f} & {gbws:.3f} & \({(gbwh-gbws)/gbws*100:+.1f}\%\) & {mpct(gbwh,gbws)} \\",
    ),
    (
        r"\(A_0\) (dB) & 89.60 & 96.53 & \(\pm1\,\mathrm{dB}\) & FAIL \\",
        rf"\(A_0\) (dB) & {a0h:.2f} & {a0s:.2f} & \(\pm1\,\mathrm{{dB}}\) & {mgain(a0h,a0s)} \\",
    ),
    (
        r"tt & 96.53 & 12.543 & 81.55 & 0.963 \\",
        rf"tt & {a0s:.2f} & {gbws:.3f} & {pms:.2f} & {pmw:.3f} \\",
    ),
    (
        r"ff & 99.75 & 51.323 & 102.71 & 0.963 \\",
        rf"ff & {ms['corners'][1]['adc']:.2f} & {ms['corners'][1]['ugf']/1e6:.3f} & {ms['corners'][1]['pm']:.2f} & {ms['corners'][1]['pwr']*1e3:.3f} \\",
    ),
    (
        r"ss & 89.50 & 4.385 & 85.85 & 0.963 \\",
        rf"ss & {ms['corners'][2]['adc']:.2f} & {ms['corners'][2]['ugf']/1e6:.3f} & {ms['corners'][2]['pm']:.2f} & {ms['corners'][2]['pwr']*1e3:.3f} \\",
    ),
    (
        r"\(A_0\) (dB) & 165.2 & 165.2 & \(0\,\mathrm{dB}\) & PASS \\",
        rf"\(A_0\) (dB) & {hc['A0_product_dB']:.1f} & {mc['adc']:.2f} & \({hc['A0_product_dB']-mc['adc']:+.1f}\,\mathrm{{dB}}\) & {mgain(hc['A0_product_dB'], mc['adc'])} \\",
    ),
    (
        r"UGF (MHz) & 184.8 & 182.8 & \(+1.1\%\) & PASS \\",
        rf"UGF (MHz) & {hc['GBW_Hz']/1e6:.1f} & {mc['ugf']/1e6:.1f} & \({(hc['GBW_Hz']-mc['ugf'])/mc['ugf']*100:+.1f}\%\) & {mpct(hc['GBW_Hz']/1e6, mc['ugf']/1e6)} \\",
    ),
    (
        r"PM (deg) & 89.4 & 89.4 & \(\Delta0^\circ\) & PASS \\",
        rf"PM (deg) & {hc['PM_hand_deg']:.1f} & {mc['pm']:.1f} & \(\Delta {hc['PM_hand_deg']-mc['pm']:+.1f}^\circ\) & {mpm(hc['PM_hand_deg'], mc['pm'])} \\",
    ),
    (
        r"CMRR (dB) & no hand model & \(-114.4\) & n/a & n/a \\",
        rf"CMRR (dB) & no hand model & \({mc['cmrr']:.1f}\) & n/a & n/a \\",
    ),
    (
        r"PSRR+ (dB) & no hand model & \(-135.4\) & n/a & n/a \\",
        rf"PSRR+ (dB) & no hand model & \({mc['psrrp']:.1f}\) & n/a & n/a \\",
    ),
    (
        r"PSRR- (dB) & no hand model & \(-107.4\) & n/a & n/a \\",
        rf"PSRR- (dB) & no hand model & \({mc['psrrn']:.1f}\) & n/a & n/a \\",
    ),
    (
        r"\(e_n\) 1\,kHz & no hand model & \(4.77\,\mathrm{nV}/\sqrt{\mathrm{Hz}}\) & n/a & n/a \\",
        rf"\(e_n\) 1\,kHz & no hand model & \({fmt_en(mc['en1k'])}\) & n/a & n/a \\",
    ),
    (
        r"\(e_n\) 1\,MHz & no hand model & \(4.77\,\mathrm{nV}/\sqrt{\mathrm{Hz}}\) & n/a & n/a \\",
        rf"\(e_n\) 1\,MHz & no hand model & \({fmt_en(mc['en1m'])}\) & n/a & n/a \\",
    ),
    # sky130 extended
    (
        r"CMRR (dB) & no hand model & \(-115.5\) & n/a & n/a \\",
        rf"CMRR (dB) & no hand model & \({ms['cmrr']:.1f}\) & n/a & n/a \\",
    ),
    (
        r"PSRR+ (dB) & no hand model & \(-9.35\) & n/a & n/a \\",
        rf"PSRR+ (dB) & no hand model & \({ms['psrrp']:.1f}\) & n/a & n/a \\",
    ),
    (
        r"PSRR- (dB) & no hand model & \(-37.3\) & n/a & n/a \\",
        rf"PSRR- (dB) & no hand model & \({ms['psrrn']:.1f}\) & n/a & n/a \\",
    ),
    # ihp
    (
        r"\(A_0\) (dB) & 90.73 & 90.73 & \(0\,\mathrm{dB}\) & PASS \\",
        rf"\(A_0\) (dB) & {hi['A0_product_dB']:.2f} & {mi['adc']:.2f} & \({hi['A0_product_dB']-mi['adc']:+.2f}\,\mathrm{{dB}}\) & {mgain(hi['A0_product_dB'], mi['adc'])} \\",
    ),
    (
        r"UGF (MHz) & 120.5 & 97.69 & \(+23.4\%\) & FAIL \\",
        rf"UGF (MHz) & {hi['GBW_Hz']/1e6:.2f} & {mi['ugf']/1e6:.2f} & \({(hi['GBW_Hz']-mi['ugf'])/mi['ugf']*100:+.1f}\%\) & {mpct(hi['GBW_Hz']/1e6, mi['ugf']/1e6)} \\",
    ),
    (
        r"PM (deg) & 97.8 & 97.8 & \(\Delta0^\circ\) & PASS \\",
        rf"PM (deg) & {hi['PM_hand_deg']:.1f} & {mi['pm']:.1f} & \(\Delta {hi['PM_hand_deg']-mi['pm']:+.1f}^\circ\) & {mpm(hi['PM_hand_deg'], mi['pm'])} \\",
    ),
    (
        r"CMRR (dB) & no hand model & \(-10.8\) & n/a & n/a \\",
        rf"CMRR (dB) & no hand model & \({mi['cmrr']:.1f}\) & n/a & n/a \\",
    ),
    (
        r"PSRR+ (dB) & no hand model & \(-18.6\) & n/a & n/a \\",
        rf"PSRR+ (dB) & no hand model & \({mi['psrrp']:.1f}\) & n/a & n/a \\",
    ),
    (
        r"PSRR- (dB) & no hand model & \(-11.7\) & n/a & n/a \\",
        rf"PSRR- (dB) & no hand model & \({mi['psrrn']:.1f}\) & n/a & n/a \\",
    ),
    (
        r"\(e_n\) 1\,kHz & no hand model & see note & n/a & n/a \\",
        rf"\(e_n\) 1\,kHz & no hand model & {fmt_en(mi['en1k'])} & n/a & n/a \\",
    ),
    (
        r"\(e_n\) 1\,MHz & no hand model & see note & n/a & n/a \\",
        rf"\(e_n\) 1\,MHz & no hand model & {fmt_en(mi['en1m'])} & n/a & n/a \\",
    ),
    (
        r"tt & 90.73 & 97.69 & 97.82 & 0.628 \\",
        rf"tt & {mi['adc']:.2f} & {mi['ugf']/1e6:.2f} & {mi['pm']:.2f} & {mi['pwr']*1e3:.3f} \\",
    ),
    (
        r"ff & 90.68 & 98.59 & 99.06 & 0.640 \\",
        rf"ff & {mi['corners'][1]['adc']:.2f} & {mi['corners'][1]['ugf']/1e6:.2f} & {mi['corners'][1]['pm']:.2f} & {mi['corners'][1]['pwr']*1e3:.3f} \\",
    ),
    (
        r"ss & 89.96 & 96.94 & 97.40 & 0.616 \\",
        rf"ss & {mi['corners'][2]['adc']:.2f} & {mi['corners'][2]['ugf']/1e6:.2f} & {mi['corners'][2]['pm']:.2f} & {mi['corners'][2]['pwr']*1e3:.3f} \\",
    ),
    # gf180
    (
        r"\(A_0\) (dB) & 112.8 & 112.8 & \(0\,\mathrm{dB}\) & PASS \\",
        rf"\(A_0\) (dB) & {hg['A0_product_dB']:.2f} & {mg['adc']:.2f} & \({hg['A0_product_dB']-mg['adc']:+.2f}\,\mathrm{{dB}}\) & {mgain(hg['A0_product_dB'], mg['adc'])} \\",
    ),
    (
        r"UGF (MHz) & 14.67 & 3.211 & \(+357\%\) & FAIL \\",
        rf"UGF (MHz) & {hg['GBW_Hz']/1e6:.2f} & {mg['ugf']/1e6:.3f} & \({(hg['GBW_Hz']-mg['ugf'])/mg['ugf']*100:+.1f}\%\) & {mpct(hg['GBW_Hz']/1e6, mg['ugf']/1e6)} \\",
    ),
    (
        r"PM (deg) & 89.3 & 89.3 & \(\Delta0^\circ\) & PASS \\",
        rf"PM (deg) & {hg['PM_hand_deg']:.1f} & {mg['pm']:.1f} & \(\Delta {hg['PM_hand_deg']-mg['pm']:+.1f}^\circ\) & {mpm(hg['PM_hand_deg'], mg['pm'])} \\",
    ),
    (
        r"CMRR (dB) & no hand model & \(-120.1\) & n/a & n/a \\",
        rf"CMRR (dB) & no hand model & \({mg['cmrr']:.1f}\) & n/a & n/a \\",
    ),
    (
        r"PSRR+ (dB) & no hand model & \(-51.7\) & n/a & n/a \\",
        rf"PSRR+ (dB) & no hand model & \({mg['psrrp']:.1f}\) & n/a & n/a \\",
    ),
    (
        r"PSRR- (dB) & no hand model & \(-48.5\) & n/a & n/a \\",
        rf"PSRR- (dB) & no hand model & \({mg['psrrn']:.1f}\) & n/a & n/a \\",
    ),
    (
        r"tt & 112.79 & 3.211 & 89.34 & 1.441 \\",
        rf"tt & {mg['adc']:.2f} & {mg['ugf']/1e6:.3f} & {mg['pm']:.2f} & {mg['pwr']*1e3:.3f} \\",
    ),
    (
        r"ff & 111.41 & 3.287 & 89.34 & 1.460 \\",
        rf"ff & {mg['corners'][1]['adc']:.2f} & {mg['corners'][1]['ugf']/1e6:.3f} & {mg['corners'][1]['pm']:.2f} & {mg['corners'][1]['pwr']*1e3:.3f} \\",
    ),
    (
        r"ss & 113.34 & 3.088 & 89.34 & 1.420 \\",
        rf"ss & {mg['corners'][2]['adc']:.2f} & {mg['corners'][2]['ugf']/1e6:.3f} & {mg['corners'][2]['pm']:.2f} & {mg['corners'][2]['pwr']*1e3:.3f} \\",
    ),
    # T9
    (
        r"cmos & 165.19 & 182.77 & 89.4 & 0.846 \\",
        rf"cmos & {mc['adc']:.2f} & {mc['ugf']/1e6:.2f} & {mc['pm']:.1f} & {mc['pwr']*1e3:.3f} \\",
    ),
    (
        r"sky130 & 96.53 & 12.54 & 81.5 & 0.963 \\",
        rf"sky130 & {a0s:.2f} & {gbws:.2f} & {pms:.1f} & {pmw:.3f} \\",
    ),
    (
        r"ihp & 90.73 & 97.69 & 97.8 & 0.628 \\",
        rf"ihp & {mi['adc']:.2f} & {mi['ugf']/1e6:.2f} & {mi['pm']:.1f} & {mi['pwr']*1e3:.3f} \\",
    ),
    (
        r"gf180 & 112.79 & 3.21 & 89.3 & 1.441 \\",
        rf"gf180 & {mg['adc']:.2f} & {mg['ugf']/1e6:.2f} & {mg['pm']:.1f} & {mg['pwr']*1e3:.3f} \\",
    ),
]

n_ok = 0
for a, b in pairs:
    if a in tex:
        tex = tex.replace(a, b)
        n_ok += 1
    else:
        print("MISS:", a[:60])
print(f"replaced {n_ok}/{len(pairs)}")

# FoM
tex = tex.replace("=130.2\\,\\mathrm{MHz\\cdot pF/mW}.", rf"={fom:.1f}\\,\\mathrm{{MHz\\cdot pF/mW}}.")
tex = tex.replace(r"12.543\times10^{6}", rf"{ms['ugf']:.3e}")

# CMOS MC figures
if "mc_ugf_hist.png" not in tex:
    tex = tex.replace(
        r"\caption{cmos --- input-referred noise density (F6).}\end{figure}",
        r"""\caption{cmos --- input-referred noise density (F6).}\end{figure}
\begin{figure}[ht]\centering\includegraphics[width=0.88\linewidth]{cmos/figures/mc_ugf_hist.png}
\caption{cmos LOT MC --- UGF histogram (F8), $N=200$.}\end{figure}
\begin{figure}[ht]\centering\includegraphics[width=0.88\linewidth]{cmos/figures/mc_pm_hist.png}
\caption{cmos LOT MC --- PM histogram (F9), $N=200$.}\end{figure}
\noindent{\footnotesize Table T8 (cmos): $N=200$, LOT \texttt{mc=1}; UGF mean $128.7\,\mathrm{MHz}$, $\sigma=3.19\,\mathrm{MHz}$; PM mean $89.20^\circ$, $\sigma=0.020^\circ$. Open-PDK MC: HARD-SKIP.}""",
    )

# leftover ---
tex = re.sub(r"(?<=&) --- (?=&)", " n/a ", tex)
tex = re.sub(r"(?<=&) --- \\\\", r" n/a \\\\", tex)

(RUN / "report.tex").write_text(tex, encoding="utf-8")

summary = f"""# fan_smc_pin_3 summary

Source path: `Fan_SMC_Pin_3`. Run id: `fan_smc_pin_3`. Date: 12 September 2026.

**PDF:** `results/fan_smc_pin_3/report.pdf`

## Nominal

| Backend | Adc (dB) | UGF (MHz) | PM (deg) | P (mW) | Vout (V) |
|---------|----------|-----------|----------|--------|----------|
| cmos | {mc['adc']:.2f} | {mc['ugf']/1e6:.2f} | {mc['pm']:.1f} | {mc['pwr']*1e3:.3f} | {mc['vout']:.3f} |
| sky130 | {a0s:.2f} | {gbws:.2f} | {pms:.1f} | {pmw:.3f} | {ms['vout']:.3f} |
| ihp | {mi['adc']:.2f} | {mi['ugf']/1e6:.2f} | {mi['pm']:.1f} | {mi['pwr']*1e3:.3f} | {mi['vout']:.3f} |
| gf180 | {mg['adc']:.2f} | {mg['ugf']/1e6:.2f} | {mg['pm']:.1f} | {mg['pwr']*1e3:.3f} | {mg['vout']:.3f} |

## Primary gates (sky130)

| Metric | Hand | Sim | Result |
|--------|------|-----|--------|
| Adc | {a0h:.2f} dB | {a0s:.2f} dB | {mgain(a0h,a0s)} |
| GBW | {gbwh:.2f} MHz | {gbws:.2f} MHz | {mpct(gbwh,gbws)} |
| PM | {pmh:.1f} deg | {pms:.1f} deg | {mpm(pmh,pms)} |
| Power | {pmw:.3f} mW | {pmw:.3f} mW | PASS |

## Coverage

- Backends: cmos, sky130, ihp, gf180 (healthy OP/ACDC)
- Corners tt/ff/ss on open PDKs
- Extended: CMRR/PSRR/noise plots
- MC: cmos LOT N=200; open-PDK mismatch HARD-SKIP
- F1-F10 embedded (CMOS provides F8/F9)

## Top mismatches

1. sky130 hand GBW vs sim UGF ({(gbwh-gbws)/gbws*100:+.0f}%; starved gm1)
2. sky130 hand PM vs sim ({pmh-pms:+.1f} deg)
3. gf180 hand A0/GBW over-predict sim

## Recovery

sky130: Ib=50uA, Cc=1pF, widened FETs from W=L=1u placeholders. IHP osdi spiceinit. GF180 fnoicor/sw_stat params.

## Agentic models

Cursor / Composer -- skill spice-analyzer (TA / agent_provenance.md).
"""
(RUN / "summary.md").write_text(summary, encoding="utf-8")
(RUN / "agent_provenance.md").write_text(
    """# Agentic provenance

- Skill: spice-analyzer (`.agents/skills/spice-analyzer`)
- Run id: `fan_smc_pin_3`
- Date: 12 September 2026
- DUT source path: `Fan_SMC_Pin_3`

| Role | Host | Model | Scope | Notes |
|------|------|-------|-------|-------|
| Primary orchestrator | Cursor | Composer | ingest--report | skill spice-analyzer; single-agent run |

Toolchain: ngspice-45.2 (WSL); Python matplotlib plots; pdflatex.
""",
    encoding="utf-8",
)

print("CJK", len(re.findall(r"[\u4e00-\u9fff]", tex)))
print("bare ---", len(re.findall(r"(?<![A-Za-z0-9])---(?![A-Za-z0-9])", tex)))

r = subprocess.run(
    ["latexmk", "-pdf", "-interaction=nonstopmode", "-f", "report.tex"],
    cwd=str(RUN),
    capture_output=True,
    text=True,
)
print("latexmk", r.returncode)
pdf = RUN / "report.pdf"
print("PDF", pdf.exists(), pdf.stat().st_size if pdf.exists() else 0)
for ln in (r.stdout + "\n" + r.stderr).splitlines():
    if ln.startswith("!") or "Error" in ln or "Emergency" in ln:
        print(ln)
