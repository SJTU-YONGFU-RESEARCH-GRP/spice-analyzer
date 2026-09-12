#!/usr/bin/env python3
"""Build CMOS / sky130 / ihp / gf180 DUT + ACDC decks for fan_smc_pin_3."""
from __future__ import annotations

from pathlib import Path

ROOT = Path("/mnt/d/proj/spice-analyzer-skill")
RUN = ROOT / "results" / "fan_smc_pin_3"
SRC = (RUN / "dut_source.sp").read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Common seed / fitted params
# ---------------------------------------------------------------------------
SEED_PARAMS = """* Seed (placeholder W=L=1u) -- overridden per backend after fit
.param MOSFET_10_1_L_gm2_PMOS=1u
.param MOSFET_10_1_M_gm2_PMOS=8
.param MOSFET_10_1_W_gm2_PMOS=1u
.param MOSFET_11_1_L_gmf2_PMOS=1u
.param MOSFET_11_1_M_gmf2_PMOS=32
.param MOSFET_11_1_W_gmf2_PMOS=1u
.param MOSFET_23_1_L_gm3_NMOS=1u
.param MOSFET_23_1_M_gm3_NMOS=16
.param MOSFET_23_1_W_gm3_NMOS=1u
.param MOSFET_8_2_L_gm1_PMOS=1u
.param MOSFET_8_2_M_gm1_PMOS=4
.param MOSFET_8_2_W_gm1_PMOS=1u
.param MOSFET_0_8_L_BIASCM_PMOS=1u
.param MOSFET_0_8_M_BIASCM_PMOS=16
.param MOSFET_0_8_W_BIASCM_PMOS=1u
.param MOSFET_17_7_L_BIASCM_NMOS=1u
.param MOSFET_17_7_M_BIASCM_NMOS=4
.param MOSFET_17_7_W_BIASCM_NMOS=1u
.param MOSFET_21_2_L_LOAD2_NMOS=1u
.param MOSFET_21_2_M_LOAD2_NMOS=4
.param MOSFET_21_2_W_LOAD2_NMOS=1u
.param CAPACITOR_0=5p
.param CURRENT_0_BIAS=60u
.param CLOAD=10p
"""

SKY_PARAMS = """* Fitted sky130 (scale=1.0u; W/L in um)
.param CURRENT_0_BIAS=50u
.param CAPACITOR_0=1p
.param CLOAD=10p
.param MOSFET_8_2_L_gm1_PMOS=0.5
.param MOSFET_8_2_W_gm1_PMOS=20
.param MOSFET_8_2_M_gm1_PMOS=8
.param MOSFET_10_1_L_gm2_PMOS=0.5
.param MOSFET_10_1_W_gm2_PMOS=16
.param MOSFET_10_1_M_gm2_PMOS=8
.param MOSFET_11_1_L_gmf2_PMOS=0.5
.param MOSFET_11_1_W_gmf2_PMOS=10
.param MOSFET_11_1_M_gmf2_PMOS=16
.param MOSFET_23_1_L_gm3_NMOS=0.5
.param MOSFET_23_1_W_gm3_NMOS=20
.param MOSFET_23_1_M_gm3_NMOS=16
.param MOSFET_0_8_L_BIASCM_PMOS=1
.param MOSFET_0_8_W_BIASCM_PMOS=4
.param MOSFET_0_8_M_BIASCM_PMOS=8
.param MOSFET_17_7_L_BIASCM_NMOS=0.5
.param MOSFET_17_7_W_BIASCM_NMOS=4
.param MOSFET_17_7_M_BIASCM_NMOS=4
.param MOSFET_21_2_L_LOAD2_NMOS=0.5
.param MOSFET_21_2_W_LOAD2_NMOS=8
.param MOSFET_21_2_M_LOAD2_NMOS=4
"""

# CMOS: meters, educational Level-1; start from similar ratios
CMOS_PARAMS = """* Fitted educational CMOS (meters)
.param CURRENT_0_BIAS=40u
.param CAPACITOR_0=2p
.param CLOAD=10p
.param MOSFET_8_2_L_gm1_PMOS=1u
.param MOSFET_8_2_W_gm1_PMOS=20u
.param MOSFET_8_2_M_gm1_PMOS=8
.param MOSFET_10_1_L_gm2_PMOS=1u
.param MOSFET_10_1_W_gm2_PMOS=16u
.param MOSFET_10_1_M_gm2_PMOS=8
.param MOSFET_11_1_L_gmf2_PMOS=1u
.param MOSFET_11_1_W_gmf2_PMOS=10u
.param MOSFET_11_1_M_gmf2_PMOS=16
.param MOSFET_23_1_L_gm3_NMOS=1u
.param MOSFET_23_1_W_gm3_NMOS=20u
.param MOSFET_23_1_M_gm3_NMOS=16
.param MOSFET_0_8_L_BIASCM_PMOS=1u
.param MOSFET_0_8_W_BIASCM_PMOS=4u
.param MOSFET_0_8_M_BIASCM_PMOS=8
.param MOSFET_17_7_L_BIASCM_NMOS=1u
.param MOSFET_17_7_W_BIASCM_NMOS=4u
.param MOSFET_17_7_M_BIASCM_NMOS=4
.param MOSFET_21_2_L_LOAD2_NMOS=1u
.param MOSFET_21_2_W_LOAD2_NMOS=8u
.param MOSFET_21_2_M_LOAD2_NMOS=4
"""

IHP_PARAMS = """* Fitted IHP SG13G2 LV (meters)
.param CURRENT_0_BIAS=40u
.param CAPACITOR_0=1.5p
.param CLOAD=10p
.param MOSFET_8_2_L_gm1_PMOS=0.45u
.param MOSFET_8_2_W_gm1_PMOS=10u
.param MOSFET_8_2_M_gm1_PMOS=8
.param MOSFET_10_1_L_gm2_PMOS=0.45u
.param MOSFET_10_1_W_gm2_PMOS=8u
.param MOSFET_10_1_M_gm2_PMOS=8
.param MOSFET_11_1_L_gmf2_PMOS=0.45u
.param MOSFET_11_1_W_gmf2_PMOS=6u
.param MOSFET_11_1_M_gmf2_PMOS=16
.param MOSFET_23_1_L_gm3_NMOS=0.45u
.param MOSFET_23_1_W_gm3_NMOS=12u
.param MOSFET_23_1_M_gm3_NMOS=16
.param MOSFET_0_8_L_BIASCM_PMOS=0.45u
.param MOSFET_0_8_W_BIASCM_PMOS=4u
.param MOSFET_0_8_M_BIASCM_PMOS=8
.param MOSFET_17_7_L_BIASCM_NMOS=0.45u
.param MOSFET_17_7_W_BIASCM_NMOS=3u
.param MOSFET_17_7_M_BIASCM_NMOS=4
.param MOSFET_21_2_L_LOAD2_NMOS=0.45u
.param MOSFET_21_2_W_LOAD2_NMOS=4u
.param MOSFET_21_2_M_LOAD2_NMOS=4
"""

GF_PARAMS = """* Fitted GF180 3.3V (meters)
.param CURRENT_0_BIAS=50u
.param CAPACITOR_0=2p
.param CLOAD=10p
.param MOSFET_8_2_L_gm1_PMOS=0.7u
.param MOSFET_8_2_W_gm1_PMOS=20u
.param MOSFET_8_2_M_gm1_PMOS=8
.param MOSFET_10_1_L_gm2_PMOS=0.7u
.param MOSFET_10_1_W_gm2_PMOS=16u
.param MOSFET_10_1_M_gm2_PMOS=8
.param MOSFET_11_1_L_gmf2_PMOS=0.7u
.param MOSFET_11_1_W_gmf2_PMOS=10u
.param MOSFET_11_1_M_gmf2_PMOS=16
.param MOSFET_23_1_L_gm3_NMOS=0.7u
.param MOSFET_23_1_W_gm3_NMOS=20u
.param MOSFET_23_1_M_gm3_NMOS=16
.param MOSFET_0_8_L_BIASCM_PMOS=0.7u
.param MOSFET_0_8_W_BIASCM_PMOS=4u
.param MOSFET_0_8_M_BIASCM_PMOS=8
.param MOSFET_17_7_L_BIASCM_NMOS=0.7u
.param MOSFET_17_7_W_BIASCM_NMOS=4u
.param MOSFET_17_7_M_BIASCM_NMOS=4
.param MOSFET_21_2_L_LOAD2_NMOS=0.7u
.param MOSFET_21_2_W_LOAD2_NMOS=8u
.param MOSFET_21_2_M_LOAD2_NMOS=4
"""


def remap_cmos(src: str) -> str:
    """X* sky130 FETs -> M* Level-1; keep node order D G S B."""
    out = []
    for line in src.splitlines():
        s = line.strip()
        if s.startswith(".subckt"):
            out.append(".subckt fan_smc_pin_3 gnda vdda vinn vinp vout")
            continue
        if s.startswith(".ends"):
            out.append(".ends fan_smc_pin_3")
            continue
        if not s.startswith("x") and not s.startswith("X"):
            # caps / current / comments
            if s.startswith("I0") or s.startswith("i0"):
                out.append("I0 net013 gnda 'CURRENT_0_BIAS'")
            elif s.startswith("C0") or s.startswith("c0"):
                out.append("C0 net050 vout 'CAPACITOR_0'")
            elif s.startswith("*") or s == "":
                out.append(line)
            else:
                out.append(line)
            continue
        # xmN D G S B model l=.. w=.. m=..
        parts = line.split()
        name = parts[0]
        d, g, snode, b = parts[1:5]
        model = parts[5]
        rest = " ".join(parts[6:])
        # extract l w m expressions
        import re

        def grab(key):
            m = re.search(rf"{key}='([^']+)'", rest, re.I)
            if not m:
                m = re.search(rf"{key}=(\S+)", rest, re.I)
            return m.group(1) if m else "1u"

        L = grab("l")
        W = grab("w")
        M = grab("m")
        if "pfet" in model:
            mod = "pmos_rvt"
        else:
            mod = "nmos_rvt"
        mname = "m" + name[1:]  # xm11 -> m11
        # ngspice Level-1: Mxxx d g s b model W= L= (no m= on some builds -- use mfactor)
        out.append(
            f"{mname} {d} {g} {snode} {b} {mod} w='{W}' l='{L}' m='{M}'"
        )
    return "\n".join(out) + "\n"


def remap_model(src: str, nmos: str, pmos: str, keep_x: bool = True) -> str:
    out = []
    for line in src.splitlines():
        s = line.strip()
        if "sky130_fd_pr__pfet_01v8" in line:
            line = line.replace("sky130_fd_pr__pfet_01v8", pmos)
        if "sky130_fd_pr__nfet_01v8" in line:
            line = line.replace("sky130_fd_pr__nfet_01v8", nmos)
        if s.startswith(".subckt"):
            line = ".subckt fan_smc_pin_3 gnda vdda vinn vinp vout"
        if s.startswith(".ends"):
            line = ".ends fan_smc_pin_3"
        # normalize I0/C0
        if s.upper().startswith("I0"):
            line = "I0 net013 gnda 'CURRENT_0_BIAS'"
        if s.upper().startswith("C0"):
            line = "C0 net050 vout 'CAPACITOR_0'"
        out.append(line)
    return "\n".join(out) + "\n"


def tb_acdc(
    backend: str,
    vdd: float,
    vcm: float,
    includes: str,
    extra_options: str = "",
    title: str = "fan_smc_pin_3 ACDC",
) -> str:
    """Unity-gain DC FB, AC open-loop, VINN drive."""
    return f"""* {title} ({backend})
{extra_options}
{includes}
.include params.sp
.include dut.sp

.param VDD={vdd}
.param VCM={vcm}

VDD vdda 0 DC {{VDD}}
VSS gnda 0 DC 0
* Common-mode bias on VINP; VINN AC-driven (inverting drive => LF phase ~180)
VINP vinp 0 DC {{VCM}} AC 0
VINN_DC vinn_dc 0 DC {{VCM}} AC 1
* DC unity-gain feedback: vout -> vinn through big L (AC open)
Lfb vout vinn 1k
Cfb vinn vinn_dc 1
Rbig vinn 0 1G
CL vout 0 {{CLOAD}}

Xdut gnda vdda vinn vinp vout fan_smc_pin_3

.control
set noaskquit
set filetype=ascii
op
let idd_op = -i(VDD)
let vout_op = v(vout)
let power_op = idd_op * {vdd}
print idd_op > ../sim/idd.txt
print vout_op > ../sim/vout_dc.txt
print power_op > ../sim/power.txt
print all > ../sim/op_nodes.txt
show m > ../sim/op_devices.txt
* AC
ac dec 50 1 1G
let mag = db(v(vout))
let ph = 180/pi*ph(v(vout))
wrdata ../figures/bode_mag.dat mag
wrdata ../figures/bode_phase.dat ph
let adc = mag[0]
print adc > ../sim/adc.txt
* UGF: first freq where mag crosses 0 from above
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
if found = 0
  echo NO_UGF > ../sim/ugf.txt
  echo NO_UGF > ../sim/ph_at_ugf.txt
else
  print ugf > ../sim/ugf.txt
  print ph_ugf > ../sim/ph_at_ugf.txt
end
quit
.endc
.end
"""


def tb_cmrr(backend, vdd, vcm, includes, extra=""):
    return f"""* CMRR AC ({backend})
{extra}
{includes}
.include params.sp
.include dut.sp
.param VDD={vdd}
.param VCM={vcm}
VDD vdda 0 DC {{VDD}}
VSS gnda 0 DC 0
* Common AC on both inputs
VINP vinp 0 DC {{VCM}} AC 1
VINN vinn 0 DC {{VCM}} AC 1
CL vout 0 {{CLOAD}}
* Force mid output bias via large R (open-loop CM)
Rbias vout 0 100Meg
Xdut gnda vdda vinn vinp vout fan_smc_pin_3
.control
set noaskquit
set filetype=ascii
ac dec 40 1 100Meg
let cmrr = db(v(vout))
wrdata ../figures/cmrr.dat cmrr
let cmrrdc = cmrr[0]
print cmrrdc > ../sim/cmrrdc.txt
quit
.endc
.end
"""


def tb_psrr(backend, vdd, vcm, includes, which: str, extra=""):
    """which = p or n"""
    if which == "p":
        vdd_line = "VDD vdda 0 DC {VDD} AC 1"
        vss_line = "VSS gnda 0 DC 0 AC 0"
        tag = "psrrp"
    else:
        vdd_line = "VDD vdda 0 DC {VDD} AC 0"
        vss_line = "VSS gnda 0 DC 0 AC 1"
        tag = "psrrn"
    return f"""* PSRR{which} ({backend})
{extra}
{includes}
.include params.sp
.include dut.sp
.param VDD={vdd}
.param VCM={vcm}
{vdd_line}
{vss_line}
VINP vinp 0 DC {{VCM}} AC 0
* unity DC FB
Lfb vout vinn 1k
Ciso vinn vinp 1
Rbig vinn 0 1G
CL vout 0 {{CLOAD}}
Xdut gnda vdda vinn vinp vout fan_smc_pin_3
.control
set noaskquit
set filetype=ascii
ac dec 40 1 100Meg
let psrr = db(v(vout))
wrdata ../figures/{tag}.dat psrr
let psrrdc = psrr[0]
print psrrdc > ../sim/{tag}_dc.txt
quit
.endc
.end
"""


def tb_noise(backend, vdd, vcm, includes, extra=""):
    return f"""* Input-referred noise ({backend})
{extra}
{includes}
.include params.sp
.include dut.sp
.param VDD={vdd}
.param VCM={vcm}
VDD vdda 0 DC {{VDD}}
VSS gnda 0 DC 0
VINP vinp 0 DC {{VCM}} AC 0
VINN_DC vinn_dc 0 DC {{VCM}} AC 0
Lfb vout vinn 1k
Cfb vinn vinn_dc 1
Rbig vinn 0 1G
CL vout 0 {{CLOAD}}
Xdut gnda vdda vinn vinp vout fan_smc_pin_3
.control
set noaskquit
set filetype=ascii
noise v(vout) VINN_DC dec 20 1 100Meg
setplot noise1
wrdata ../figures/noise.dat inoise_spectrum
* spots via noise2 integrated? print density at indices near 1k/1M later in python
quit
.endc
.end
"""


# Includes
SKY_INC_TT = """
.option scale=1.0u
.param mc_mm_switch=0
.param mc_pr_switch=0
.include '../../../models/pdk/sky130_fd_pr/models/parameters/lod.spice'
.include '../../../models/pdk/sky130_fd_pr/cells/nfet_01v8/sky130_fd_pr__nfet_01v8__mismatch.corner.spice'
.include '../../../models/pdk/sky130_fd_pr/cells/pfet_01v8/sky130_fd_pr__pfet_01v8__mismatch.corner.spice'
.include '../../../models/pdk/sky130_fd_pr/cells/nfet_01v8/sky130_fd_pr__nfet_01v8__tt.pm3.spice'
.include '../../../models/pdk/sky130_fd_pr/cells/pfet_01v8/sky130_fd_pr__pfet_01v8__tt.pm3.spice'
"""

CMOS_INC = """
.include '../../../models/cmos.lib'
"""

IHP_INC = """
.lib '../../../models/pdk/ihp-sg13g2/ihp-sg13g2/libs.tech/ngspice/models/cornerMOSlv.lib' mos_tt
"""

GF_INC = """
.lib '../../../models/pdk/gf180mcu_fd_pr/models/ngspice/sm141064.ngspice' typical
"""


def write_backend(name, params, dut, vdd, vcm, includes, extra=""):
    b = RUN / name
    (b / "tb").mkdir(parents=True, exist_ok=True)
    (b / "sim").mkdir(parents=True, exist_ok=True)
    (b / "figures").mkdir(parents=True, exist_ok=True)
    (b / "tb" / "params.sp").write_text(params, encoding="utf-8")
    (b / "tb" / "dut.sp").write_text(dut, encoding="utf-8")
    (b / "tb" / "tb_acdc.sp").write_text(
        tb_acdc(name, vdd, vcm, includes, extra), encoding="utf-8"
    )
    (b / "tb" / "tb_cmrr.sp").write_text(
        tb_cmrr(name, vdd, vcm, includes, extra), encoding="utf-8"
    )
    (b / "tb" / "tb_psrrp.sp").write_text(
        tb_psrr(name, vdd, vcm, includes, "p", extra), encoding="utf-8"
    )
    (b / "tb" / "tb_psrrn.sp").write_text(
        tb_psrr(name, vdd, vcm, includes, "n", extra), encoding="utf-8"
    )
    (b / "tb" / "tb_noise.sp").write_text(
        tb_noise(name, vdd, vcm, includes, extra), encoding="utf-8"
    )
    print("wrote", name)


def main():
    (RUN / "seed_params.sp").write_text(SEED_PARAMS, encoding="utf-8")

    write_backend(
        "cmos",
        CMOS_PARAMS,
        remap_cmos(SRC),
        1.8,
        0.9,
        CMOS_INC,
    )
    write_backend(
        "sky130",
        SKY_PARAMS,
        remap_model(SRC, "sky130_fd_pr__nfet_01v8", "sky130_fd_pr__pfet_01v8"),
        1.8,
        0.9,
        SKY_INC_TT,
    )
    write_backend(
        "ihp",
        IHP_PARAMS,
        remap_model(SRC, "sg13_lv_nmos", "sg13_lv_pmos"),
        1.2,
        0.6,
        IHP_INC,
    )
    # IHP spiceinit
    ihp_init = RUN / "ihp" / "tb" / ".spiceinit"
    osdi = ROOT / "models/pdk/ihp-sg13g2/ihp-sg13g2/libs.tech/ngspice/osdi"
    ihp_init.write_text(
        "\n".join(
            f"osdi {osdi / f}"
            for f in [
                "psp103.osdi",
                "psp103_nqs.osdi",
                "mosvar.osdi",
                "r3_cmc.osdi",
                "cap_cmomi.osdi",
                "cap_cmomf.osdi",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_backend(
        "gf180",
        GF_PARAMS,
        remap_model(SRC, "nmos_3p3", "pmos_3p3"),
        3.3,
        1.65,
        GF_INC,
    )
    print("done")


if __name__ == "__main__":
    main()
