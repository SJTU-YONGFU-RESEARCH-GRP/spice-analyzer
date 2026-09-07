import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

base = Path(r"d:\proj\spice-analyzer\results\Alfio_RAFFC_Pin_3_20260907_1745\figures")

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
fig, ax = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
ax[0].semilogx(f, m)
ax[0].set_ylabel("Mag (dB)")
ax[0].grid(True, which="both", ls=":")
ax[0].set_title("Alfio_RAFFC_Pin_3 ADM AC (stock AnalogGym sizing)")
ax[1].semilogx(f, [p * 180 / 3.14159265 for p in ph])
ax[1].set_ylabel("Phase (deg)")
ax[1].set_xlabel("Frequency (Hz)")
ax[1].grid(True, which="both", ls=":")
fig.tight_layout()
out = base / "bode.png"
fig.savefig(out, dpi=150)
print("wrote", out, "points", len(f))
