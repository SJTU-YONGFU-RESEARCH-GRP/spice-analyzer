* PSRRn (ihp)


.lib '../../../../models/pdk/ihp-sg13g2/ihp-sg13g2/libs.tech/ngspice/models/cornerMOSlv.lib' mos_tt

.include params.sp
.include dut.sp
.param VDD=1.2
.param VCM=0.6
VDD vdda 0 DC {VDD} AC 0
VSS gnda 0 DC 0 AC 1
VINP vinp 0 DC {VCM} AC 0
* unity DC FB
Lfb vout vinn 1k
Ciso vinn vinp 1
Rbig vinn 0 1G
CL vout 0 {CLOAD}
Xdut gnda vdda vinn vinp vout fan_smc_pin_3
.control
set noaskquit
set filetype=ascii
ac dec 40 1 100Meg
let psrr = db(v(vout))
wrdata ../figures/psrrn.dat psrr
let psrrdc = psrr[0]
print psrrdc > ../sim/psrrn_dc.txt
quit
.endc
.end
