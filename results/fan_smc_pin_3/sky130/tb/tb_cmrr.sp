* CMRR AC (sky130)


.option scale=1.0u
.param mc_mm_switch=0
.param mc_pr_switch=0
.include '../../../../models/pdk/sky130_fd_pr/models/parameters/lod.spice'
.include '../../../../models/pdk/sky130_fd_pr/cells/nfet_01v8/sky130_fd_pr__nfet_01v8__mismatch.corner.spice'
.include '../../../../models/pdk/sky130_fd_pr/cells/pfet_01v8/sky130_fd_pr__pfet_01v8__mismatch.corner.spice'
.include '../../../../models/pdk/sky130_fd_pr/cells/nfet_01v8/sky130_fd_pr__nfet_01v8__tt.pm3.spice'
.include '../../../../models/pdk/sky130_fd_pr/cells/pfet_01v8/sky130_fd_pr__pfet_01v8__tt.pm3.spice'

.include params.sp
.include dut.sp
.param VDD=1.8
.param VCM=0.9
VDD vdda 0 DC {VDD}
VSS gnda 0 DC 0
* Common AC on both inputs
VINP vinp 0 DC {VCM} AC 1
VINN vinn 0 DC {VCM} AC 1
CL vout 0 {CLOAD}
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
