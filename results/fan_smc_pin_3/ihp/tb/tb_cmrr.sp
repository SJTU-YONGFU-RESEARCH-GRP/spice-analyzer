* CMRR AC (ihp)


.lib '../../../../models/pdk/ihp-sg13g2/ihp-sg13g2/libs.tech/ngspice/models/cornerMOSlv.lib' mos_tt

.include params.sp
.include dut.sp
.param VDD=1.2
.param VCM=0.6
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
