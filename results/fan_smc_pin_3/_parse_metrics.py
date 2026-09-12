#!/usr/bin/env python3
"""Parse OP/AC metrics from sim outputs into metrics.json / metrics.md."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

RUN = Path("/mnt/d/proj/spice-analyzer-skill/results/fan_smc_pin_3")
VDD = {"cmos": 1.8, "sky130": 1.8, "ihp": 1.2, "gf180": 3.3}


def grabf(path: Path):
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


def from_op_nodes(sim: Path):
    p = sim / "op_nodes.txt"
    if not p.exists():
        return None, None
    vout = None
    idd = None
    for line in p.read_text(errors="replace").splitlines():
        if line.startswith("vout ") or line.startswith("vout="):
            vout = float(line.split("=")[1].strip())
        if "vdd#branch" in line:
            idd = -float(line.split("=")[1].strip())
    return vout, idd


def gm_gds(sim: Path, names):
    """Parse show m dump for device gm/gds. names: list of substrings."""
    p = sim / "op_devices.txt"
    if not p.exists():
        return {}
    lines = p.read_text(errors="replace").splitlines()
    # Find header line with device names
    out = {}
    header_idx = None
    devices = []
    for i, l in enumerate(lines):
        if "device" in l.lower() and any(n.lower() in l.lower() for n in names):
            # often: device  mm8  mm9 ...
            parts = l.split()
            devices = parts[1:]
            header_idx = i
            break
    if header_idx is None:
        # try multi-column blocks: search each name
        text = "\n".join(lines)
        for n in names:
            gm = None
            gds = None
            for i, l in enumerate(lines):
                if n.lower() in l.lower() and ("---" in l or l.strip().startswith(n) or "device" in l.lower()):
                    # look ahead for gm/gds rows in same column - hard; skip
                    pass
            out[n] = {"gm": gm, "gds": gds}
        return out

    # Collect parameter rows
    params = {}
    for l in lines[header_idx + 1 :]:
        if not l.strip():
            continue
        if l.lower().startswith("device"):
            break
        parts = l.split()
        if len(parts) < 2:
            continue
        key = parts[0].lower()
        vals = []
        for x in parts[1:]:
            try:
                vals.append(float(x))
            except ValueError:
                vals.append(None)
        params[key] = vals

    for n in names:
        # find column
        col = None
        for j, d in enumerate(devices):
            if n.lower() in d.lower():
                col = j
                break
        if col is None:
            continue
        gm = params.get("gm", [None] * (col + 1))
        gds = params.get("gds", [None] * (col + 1))
        out[n] = {
            "gm": gm[col] if col < len(gm) else None,
            "gds": gds[col] if col < len(gds) else None,
        }
    return out


def pm_from_ph(ph):
    if ph is None:
        return None
    if -180 <= ph <= 0:
        return 180.0 + ph
    # VINN drive often gives LF ~0 and UGF near +90..-90 depending
    if 0 < ph < 180:
        return ph  # already phase margin-like for some conventions
    return ph


def process(be: str):
    sim = RUN / be / "sim"
    fig = RUN / be / "figures"
    vdd = VDD[be]
    adc = grabf(sim / "adc.txt")
    ugf = grabf(sim / "ugf.txt")
    ph = grabf(sim / "ph_at_ugf.txt")
    vout, idd = from_op_nodes(sim)
    if idd is None:
        raw = grabf(sim / "idd_raw.txt")
        if raw is not None:
            idd = -raw if raw < 0 else abs(raw)  # branch is usually negative for source
            if raw > 0:
                idd = raw  # unlikely
            else:
                idd = -raw
    # Write idd/power/vout for convenience
    if idd is not None:
        (sim / "idd.txt").write_text(f"idd = {idd}\n")
        (sim / "power.txt").write_text(f"power = {idd * vdd}\n")
    if vout is not None:
        (sim / "vout_dc.txt").write_text(f"vout = {vout}\n")

    # device gm: try mm8/xm8 etc
    keys = ["mm8", "xm8", "mm10", "xm10", "mm23", "xm23", "mm11", "xm11"]
    gms = gm_gds(sim, keys)

    def pick(pref):
        for k, v in gms.items():
            if pref in k.lower() and v.get("gm") is not None:
                return v
        return {"gm": None, "gds": None}

    g1 = pick("m8") if pick("m8").get("gm") else pick("8")
    # better: explicit
    def getdev(substr):
        for k, v in gms.items():
            if substr in k.lower():
                return v
        return {"gm": None, "gds": None}

    d8 = getdev("m8") or getdev("8")
    # Prefer exact
    for cand in ["mm8", "xm8", "m.xdut.mm8", "m.xdut.xm8"]:
        if cand in gms:
            d8 = gms[cand]
            break
    d10 = None
    d23 = None
    d11 = None
    for k, v in gms.items():
        kl = k.lower()
        if "m10" in kl or kl.endswith("10"):
            d10 = v
        if "m23" in kl or kl.endswith("23"):
            d23 = v
        if "m11" in kl or kl.endswith("11"):
            d11 = v
    d8 = d8 or {"gm": None, "gds": None}
    d10 = d10 or {"gm": None, "gds": None}
    d23 = d23 or {"gm": None, "gds": None}
    d11 = d11 or {"gm": None, "gds": None}

    pm = pm_from_ph(ph)
    # For VINN-drive: if phase at UGF is near +90, PM ≈ ph (unusual); if near -90, PM=180+ph
    # Prior convention: PM = 180 + ph when ph negative
    if ph is not None and ph > 0 and ph < 180:
        # bode phase often wraps; educational Level-1 gave ~89 deg -> treat as PM
        pm = ph

    m = {
        "backend": be,
        "corner": "nominal",
        "Adc_dB": adc,
        "UGF_Hz": ugf,
        "phase_at_UGF_deg": ph,
        "PM_deg": pm,
        "Idd_A": idd,
        "Power_W": (idd * vdd if idd is not None else None),
        "Vout_DC": vout,
        "gm1_S": d8.get("gm"),
        "gds1_S": d8.get("gds"),
        "gm2_S": d10.get("gm"),
        "gds2_S": d10.get("gds"),
        "gm3_S": d23.get("gm"),
        "gds3_S": d23.get("gds"),
        "gmf_S": d11.get("gm"),
        "gdsf_S": d11.get("gds"),
        "healthy": bool(
            adc
            and adc > 20
            and ugf
            and ugf > 0
            and vout is not None
            and 0.05 * vdd < vout < 0.95 * vdd
        ),
    }
    (sim / "metrics.json").write_text(json.dumps(m, indent=2))
    lines = [f"# Metrics ({be})", ""]
    for k, v in m.items():
        lines.append(f"- {k}: {v}")
    (sim / "metrics.md").write_text("\n".join(lines) + "\n")
    print(be, m)
    return m


def main():
    allm = {}
    for be in ["cmos", "sky130", "ihp", "gf180"]:
        if (RUN / be / "sim" / "adc.txt").exists() or (RUN / be / "sim" / "op_nodes.txt").exists():
            allm[be] = process(be)
    (RUN / "sim_backend_metrics.json").write_text(json.dumps(allm, indent=2))


if __name__ == "__main__":
    main()
