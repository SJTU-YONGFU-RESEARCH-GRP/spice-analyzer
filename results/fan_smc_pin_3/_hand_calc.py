#!/usr/bin/env python3
import math
from pathlib import Path

def parse_show_m(path):
    devices = {}
    headers = []
    for line in Path(path).read_text(errors="replace").splitlines():
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

def get(devs, tok):
    for n, d in devs.items():
        if tok in n:
            return d
    return {}

devs = parse_show_m("sky130/sim/op_devices.txt")
for tok in ["xm8", "xm9", "xm10", "xm11", "xm23", "xm6", "xm16", "xm20", "xm21", "xm22", "xm7"]:
    d = get(devs, tok)
    print(tok, {k: d.get(k) for k in ("gm", "gds", "id")})

gm1 = get(devs, "xm8")["gm"]
gm2 = get(devs, "xm10")["gm"]
gm3 = get(devs, "xm23")["gm"]
gmf = get(devs, "xm11")["gm"]
gds6 = get(devs, "xm6")["gds"]
gm16 = get(devs, "xm16")["gm"]
gds16 = get(devs, "xm16")["gds"]
gds20 = get(devs, "xm20")["gds"]
gds22 = get(devs, "xm22")["gds"]
gds7 = get(devs, "xm7")["gds"]
gds23 = get(devs, "xm23")["gds"]
gds11 = get(devs, "xm11")["gds"]

ro16 = 1 / gds16
ro20 = 1 / gds20
ro6 = 1 / gds6
Rcas = gm16 * ro16 * ro20
Rout1 = 1 / (1 / Rcas + 1 / ro6)
Av1 = gm1 * Rout1
Rout2 = 1 / (gds22 + gds7)
Av2 = gm2 * Rout2
Rout3 = 1 / (gds23 + gds11)
Av3 = gm3 * Rout3
A0 = Av1 * Av2 * Av3
print(f"Rout1={Rout1:.4e} Av1={Av1:.4e} ({20*math.log10(Av1):.2f} dB)")
print(f"Rout2={Rout2:.4e} Av2={Av2:.4e} ({20*math.log10(Av2):.2f} dB)")
print(f"Rout3={Rout3:.4e} Av3={Av3:.4e} ({20*math.log10(Av3):.2f} dB)")
print(f"A0={A0:.4e} ({20*math.log10(A0):.2f} dB)")

Cc = 1e-12
CL = 10e-12
GBW = gm1 / (2 * math.pi * Cc)
fp2 = gm2 / (2 * math.pi * Cc)
fp3 = gm3 / (2 * math.pi * CL)
fz = gmf / (2 * math.pi * Cc)
wt = 2 * math.pi * GBW
t2 = math.degrees(math.atan(GBW / fp2))
t3 = math.degrees(math.atan(GBW / fp3))
tz = math.degrees(math.atan(GBW / fz))
PM = 90 - t2 - t3 + tz
print(f"GBW={GBW/1e6:.3f} MHz fp2={fp2/1e6:.2f} fp3={fp3/1e6:.2f} fz={fz/1e6:.2f}")
print(f"atan {t2:.2f} {t3:.2f} {tz:.2f} PM={PM:.2f}")

# bias currents from OP
print("Id xm8", get(devs,"xm8")["id"], "xm10", get(devs,"xm10")["id"], "xm23", get(devs,"xm23")["id"], "xm11", get(devs,"xm11")["id"])
