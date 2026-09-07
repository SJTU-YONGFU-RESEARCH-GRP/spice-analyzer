from pathlib import Path
import math

base = Path("/mnt/d/proj/spice-analyzer/results/Alfio_RAFFC_Pin_3_20260907_1745/figures")

def load(p):
    f, y = [], []
    for line in Path(p).read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                f.append(float(parts[0]))
                y.append(float(parts[1]))
            except ValueError:
                pass
    return f, y

f, m = load(base / "bode_mag.dat")
_, ph = load(base / "bode_phase.dat")
ph_deg = [p * 180 / math.pi for p in ph]

W, H, ml, mr, mt, mb = 900, 620, 70, 30, 40, 50
plot_w = W - ml - mr
plot_h1 = 240
plot_h2 = 240
gap = 30


def xmap(fv):
    l0, l1 = math.log10(f[0]), math.log10(f[-1])
    return ml + (math.log10(fv) - l0) / (l1 - l0) * plot_w


def ymap1(v, vmin=-110, vmax=10):
    y0 = mt + plot_h1
    return y0 - (v - vmin) / (vmax - vmin) * plot_h1


def ymap2(v, vmin=-200, vmax=200):
    y0 = mt + plot_h1 + gap + plot_h2
    return y0 - (v - vmin) / (vmax - vmin) * plot_h2

poly1 = " ".join(f"{xmap(a):.1f},{ymap1(b):.1f}" for a, b in zip(f, m))
poly2 = " ".join(f"{xmap(a):.1f},{ymap2(b):.1f}" for a, b in zip(f, ph_deg))

svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">
  <rect width="100%" height="100%" fill="white"/>
  <text x="{W/2}" y="24" text-anchor="middle" font-family="Helvetica" font-size="16">Alfio_RAFFC_Pin_3 ADM AC (stock sizing)</text>
  <rect x="{ml}" y="{mt}" width="{plot_w}" height="{plot_h1}" fill="none" stroke="#333"/>
  <polyline fill="none" stroke="#1f77b4" stroke-width="2" points="{poly1}"/>
  <text x="20" y="{mt + plot_h1/2}" transform="rotate(-90 20,{mt + plot_h1/2})" font-family="Helvetica" font-size="12">Mag (dB)</text>
  <rect x="{ml}" y="{mt + plot_h1 + gap}" width="{plot_w}" height="{plot_h2}" fill="none" stroke="#333"/>
  <polyline fill="none" stroke="#d62728" stroke-width="2" points="{poly2}"/>
  <text x="20" y="{mt + plot_h1 + gap + plot_h2/2}" transform="rotate(-90 20,{mt + plot_h1 + gap + plot_h2/2})" font-family="Helvetica" font-size="12">Phase (deg)</text>
  <text x="{W/2}" y="{H-15}" text-anchor="middle" font-family="Helvetica" font-size="12">Frequency (Hz)</text>
</svg>
'''
out = base / "bode.svg"
out.write_text(svg, encoding="utf-8")
print("wrote", out)
