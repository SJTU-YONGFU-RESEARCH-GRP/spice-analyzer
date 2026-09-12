#!/usr/bin/env python3
from pathlib import Path
import subprocess

RUN = Path("/mnt/d/proj/spice-analyzer-skill/results/fan_smc_pin_3")
tex = (RUN / "report.tex").read_text(encoding="utf-8")

vals = {
    "cmos": (5.72560824e-09, 5.72579653e-09),
    "sky130": (2.41242573e-06, 1.69205732e-07),
    "ihp": (6.47978904e-19, 6.47978904e-22),
    "gf180": (3.05748472e-06, 1.30341101e-07),
}


def en_cell(v: float) -> str:
    if v < 1e-15:
        return "HARD-SKIP: numerical floor"
    if v >= 1e-6:
        return f"({v*1e6:.2f} uV/rtHz)"
    return f"({v*1e9:.2f} nV/rtHz)"


lines = tex.splitlines()
be = "cmos"
out = []
for line in lines:
    if "Results --- educational CMOS" in line:
        be = "cmos"
    elif "Results --- sky130" in line:
        be = "sky130"
    elif "Results --- IHP" in line:
        be = "ihp"
    elif "Results --- GF180" in line:
        be = "gf180"
    if r"\(e_n\) 1\,kHz" in line and "no hand model" in line:
        out.append(
            rf"\(e_n\) 1\,kHz & no hand model & {en_cell(vals[be][0])} & n/a & n/a \\"
        )
    elif r"\(e_n\) 1\,MHz" in line and "no hand model" in line:
        out.append(
            rf"\(e_n\) 1\,MHz & no hand model & {en_cell(vals[be][1])} & n/a & n/a \\"
        )
    else:
        out.append(line)

tex = "\n".join(out) + "\n"
# fix double &= in OP gm align (second amp on same line)
tex = tex.replace(
    r"g_{m1}&=4.46582e-05\,\mathrm{S},\quad g_{m2}&=8.27011e-04\,\mathrm{S},\\",
    r"g_{m1}&=4.46582\times10^{-5}\,\mathrm{S},\quad g_{m2}=8.27011\times10^{-4}\,\mathrm{S},\\",
)
tex = tex.replace(
    r"g_{m3}&=1.44722e-03\,\mathrm{S},\quad g_{mf}&=1.03929e-03\,\mathrm{S}.",
    r"g_{m3}&=1.44722\times10^{-3}\,\mathrm{S},\quad g_{mf}=1.03929\times10^{-3}\,\mathrm{S}.",
)
# also if already partially fixed
tex = tex.replace(
    r"g_{m1}&=4.46582\times10^{-5}\,\mathrm{S},\quad g_{m2}&=8.27011\times10^{-4}\,\mathrm{S},\\",
    r"g_{m1}&=4.46582\times10^{-5}\,\mathrm{S},\quad g_{m2}=8.27011\times10^{-4}\,\mathrm{S},\\",
)
tex = tex.replace(
    r"g_{m3}&=1.44722\times10^{-3}\,\mathrm{S},\quad g_{mf}&=1.03929\times10^{-3}\,\mathrm{S}.",
    r"g_{m3}&=1.44722\times10^{-3}\,\mathrm{S},\quad g_{mf}=1.03929\times10^{-3}\,\mathrm{S}.",
)

(RUN / "report.tex").write_text(tex, encoding="utf-8")
for i, line in enumerate(tex.splitlines(), 1):
    if "e_n" in line and "no hand" in line:
        print(i, line)

r = subprocess.run(
    ["latexmk", "-pdf", "-interaction=nonstopmode", "-f", "report.tex"],
    cwd=str(RUN),
    capture_output=True,
    text=True,
)
print("rc", r.returncode)
pdf = RUN / "report.pdf"
print("pdf", pdf.exists(), pdf.stat().st_size if pdf.exists() else 0)
for ln in (r.stdout + r.stderr).splitlines():
    if ln.startswith("!") or "Output written" in ln or "Fatal" in ln:
        print(ln)
