#!/usr/bin/env python3
"""Rewrite ACDC/extended TBs with proven large-L isolation + absolute model paths."""
from __future__ import annotations

from pathlib import Path

ROOT = Path("/mnt/d/proj/spice-analyzer-skill")
RUN = ROOT / "results/fan_smc_pin_3"

SKY = ROOT / "models/pdk/sky130_fd_pr"
IHP = ROOT / "models/pdk/ihp-sg13g2/ihp-sg13g2/libs.tech/ngspice"
GF = ROOT / "models/pdk/gf180mcu_fd_pr/models/ngspice"


def sky_inc(corner: str = "tt") -> str:
    return f"""
.option scale=1.0u
.param mc_mm_switch=0
.param mc_pr_switch=0
.include '{SKY}/models/parameters/lod.spice'
.include '{SKY}/cells/nfet_01v8/sky130_fd_pr__nfet_01v8__mismatch.corner.spice'
.include '{SKY}/cells/pfet_01v8/sky130_fd_pr__pfet_01v8__mismatch.corner.spice'
.include '{SKY}/cells/nfet_01v8/sky130_fd_pr__nfet_01v8__{corner}.pm3.spice'
.include '{SKY}/cells/pfet_01v8/sky130_fd_pr__pfet_01v8__{corner}.pm3.spice'
"""


def gf_inc(corner: str = "typical") -> str:
    return f".lib '{GF}/sm141064.ngspice' {corner}\n"


def ihp_inc(corner: str = "mos_tt") -> str:
    return f".lib '{IHP}/models/cornerMOSlv.lib' {corner}\n"


CMOS_INC = f".include '{ROOT}/models/cmos.lib'\n"


def acdc_ctrl(vdd: float) -> str:
    return f"""
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
ac dec 50 1 1e10
let mag = vdb(vout)
let ph_deg = vp(vout)*180/pi
wrdata ../figures/bode_mag.dat mag
wrdata ../figures/bode_phase.dat ph_deg
let Adc = mag[0]
print Adc > ../sim/adc.txt
let found = 0
let n = length(mag)
let i = 1
while i < n
  if mag[i] < 0
    if found eq 0
      if mag[i-1] >= 0
        let f1 = frequency[i-1]
        let f2 = frequency[i]
        let m1 = mag[i-1]
        let m2 = mag[i]
        let ugf = f1 + (f2-f1)*m1/(m1-m2)
        let ph_at = ph_deg[i-1] + (ph_deg[i]-ph_deg[i-1])*(ugf-f1)/(f2-f1)
        let found = 1
      end
    end
  end
  let i = i + 1
end
if found eq 1
  print ugf > ../sim/ugf.txt
  print ph_at > ../sim/ph_at_ugf.txt
else
  echo NO_UGF > ../sim/ugf.txt
  echo NO_UGF > ../sim/ph_at_ugf.txt
end
print idd_op > ../sim/idd.txt
print power_op > ../sim/power.txt
print vout_op > ../sim/vout_dc.txt
quit
.endc
.end
"""


def acdc_deck(title: str, includes: str, vdd: float, vcm: float) -> str:
    return f"""* {title}
* Unity-gain DC FB via large L; AC open-loop; VINN AC drive
{includes}
.include params.sp
.include dut.sp
.param VDD={vdd}
.param VCM={vcm}
.temp 27
VDD vdda 0 DC {{VDD}}
VSS gnda 0 DC 0
VCM vinp 0 DC {{VCM}}
* DC unity-gain feedback (large L keeps AC open-loop)
Lfb vout vinn 1e9
Rdummy vinn 0 1e12
Cac vinn vac 1
Vac vac 0 DC 0 AC 1
CL vout 0 {{CLOAD}}
Xdut gnda vdda vinn vinp vout fan_smc_pin_3
{acdc_ctrl(vdd)}
"""


def cmrr_deck(includes: str, vdd: float, vcm: float) -> str:
    return f"""* CMRR AC
{includes}
.include params.sp
.include dut.sp
.param VDD={vdd}
.param VCM={vcm}
VDD vdda 0 DC {{VDD}}
VSS gnda 0 DC 0
VINP vinp 0 DC {{VCM}} AC 1
VINN vinn 0 DC {{VCM}} AC 1
CL vout 0 {{CLOAD}}
Rbias vout 0 100Meg
Xdut gnda vdda vinn vinp vout fan_smc_pin_3
.control
set noaskquit
set filetype=ascii
ac dec 40 1 100Meg
let cmrr = vdb(vout)
wrdata ../figures/cmrr.dat cmrr
let cmrrdc = cmrr[0]
print cmrrdc > ../sim/cmrrdc.txt
quit
.endc
.end
"""


def psrr_deck(includes: str, vdd: float, vcm: float, which: str) -> str:
    if which == "p":
        vdd_line = "VDD vdda 0 DC {VDD} AC 1"
        vss_line = "VSS gnda 0 DC 0 AC 0"
        tag = "psrrp"
    else:
        vdd_line = "VDD vdda 0 DC {VDD} AC 0"
        vss_line = "VSS gnda 0 DC 0 AC 1"
        tag = "psrrn"
    return f"""* PSRR{which}
{includes}
.include params.sp
.include dut.sp
.param VDD={vdd}
.param VCM={vcm}
{vdd_line}
{vss_line}
VINP vinp 0 DC {{VCM}} AC 0
Lfb vout vinn 1e9
Rdummy vinn 0 1e12
CL vout 0 {{CLOAD}}
Xdut gnda vdda vinn vinp vout fan_smc_pin_3
.control
set noaskquit
set filetype=ascii
ac dec 40 1 100Meg
let psrr = vdb(vout)
wrdata ../figures/{tag}.dat psrr
let psrrdc = psrr[0]
print psrrdc > ../sim/{tag}_dc.txt
quit
.endc
.end
"""


def noise_deck(includes: str, vdd: float, vcm: float) -> str:
    return f"""* Input-referred noise
{includes}
.include params.sp
.include dut.sp
.param VDD={vdd}
.param VCM={vcm}
VDD vdda 0 DC {{VDD}}
VSS gnda 0 DC 0
VINP vinp 0 DC {{VCM}} AC 0
Vac vac 0 DC 0 AC 0
Lfb vout vinn 1e9
Rdummy vinn 0 1e12
Cac vinn vac 1
CL vout 0 {{CLOAD}}
Xdut gnda vdda vinn vinp vout fan_smc_pin_3
.control
set noaskquit
set filetype=ascii
noise v(vout) Vac dec 20 1 100Meg
setplot noise1
wrdata ../figures/noise.dat inoise_spectrum
quit
.endc
.end
"""


def main() -> None:
    backends = {
        "cmos": (1.8, 0.9, CMOS_INC, None),
        "sky130": (
            1.8,
            0.9,
            sky_inc("tt"),
            {"tt": sky_inc("tt"), "ff": sky_inc("ff"), "ss": sky_inc("ss")},
        ),
        "ihp": (
            1.2,
            0.6,
            ihp_inc("mos_tt"),
            {
                "tt": ihp_inc("mos_tt"),
                "ff": ihp_inc("mos_ff"),
                "ss": ihp_inc("mos_ss"),
            },
        ),
        "gf180": (
            3.3,
            1.65,
            gf_inc("typical"),
            {
                "tt": gf_inc("typical"),
                "ff": gf_inc("ff"),
                "ss": gf_inc("ss"),
            },
        ),
    }

    for be, (vdd, vcm, inc, corners) in backends.items():
        tb = RUN / be / "tb"
        (tb / "tb_acdc.sp").write_text(acdc_deck(f"fan_smc_pin_3 ACDC {be}", inc, vdd, vcm))
        (tb / "tb_cmrr.sp").write_text(cmrr_deck(inc, vdd, vcm))
        (tb / "tb_psrrp.sp").write_text(psrr_deck(inc, vdd, vcm, "p"))
        (tb / "tb_psrrn.sp").write_text(psrr_deck(inc, vdd, vcm, "n"))
        (tb / "tb_noise.sp").write_text(noise_deck(inc, vdd, vcm))
        if corners:
            for cname, cinc in corners.items():
                (tb / f"tb_acdc_{cname}.sp").write_text(
                    acdc_deck(f"fan_smc_pin_3 ACDC {be} {cname}", cinc, vdd, vcm)
                )
        print("updated TBs", be)

    osdi = IHP / "osdi"
    init = RUN / "ihp" / "tb" / ".spiceinit"
    lines = []
    for f in [
        "psp103.osdi",
        "psp103_nqs.osdi",
        "mosvar.osdi",
        "r3_cmc.osdi",
        "cap_cmomi.osdi",
        "cap_cmomf.osdi",
    ]:
        p = osdi / f
        if p.exists():
            lines.append(f"pre_osdi {p}")
    init.write_text("\n".join(lines) + "\n")
    print("ihp .spiceinit ok", len(lines), "osdi")

    cmos_params = """* Fitted educational CMOS (meters) -- healthy OP target Idd~0.3-0.5mA Vout~0.9
.param CURRENT_0_BIAS=40u
.param CAPACITOR_0=2p
.param CLOAD=10p
.param MOSFET_8_2_L_gm1_PMOS=0.5u
.param MOSFET_8_2_W_gm1_PMOS=20u
.param MOSFET_8_2_M_gm1_PMOS=8
.param MOSFET_10_1_L_gm2_PMOS=0.5u
.param MOSFET_10_1_W_gm2_PMOS=16u
.param MOSFET_10_1_M_gm2_PMOS=8
.param MOSFET_11_1_L_gmf2_PMOS=0.5u
.param MOSFET_11_1_W_gmf2_PMOS=10u
.param MOSFET_11_1_M_gmf2_PMOS=16
.param MOSFET_23_1_L_gm3_NMOS=0.5u
.param MOSFET_23_1_W_gm3_NMOS=20u
.param MOSFET_23_1_M_gm3_NMOS=16
.param MOSFET_0_8_L_BIASCM_PMOS=1u
.param MOSFET_0_8_W_BIASCM_PMOS=4u
.param MOSFET_0_8_M_BIASCM_PMOS=8
.param MOSFET_17_7_L_BIASCM_NMOS=0.5u
.param MOSFET_17_7_W_BIASCM_NMOS=4u
.param MOSFET_17_7_M_BIASCM_NMOS=4
.param MOSFET_21_2_L_LOAD2_NMOS=0.5u
.param MOSFET_21_2_W_LOAD2_NMOS=8u
.param MOSFET_21_2_M_LOAD2_NMOS=4
"""
    (RUN / "cmos" / "tb" / "params.sp").write_text(cmos_params)
    print("done")


if __name__ == "__main__":
    main()
