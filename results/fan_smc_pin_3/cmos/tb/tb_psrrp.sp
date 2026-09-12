* PSRRp (cmos)


.include '../../../../models/cmos.lib'

.include params.sp
.include dut.sp
.param VDD=1.8
.param VCM=0.9
VDD vdda 0 DC {VDD} AC 1
VSS gnda 0 DC 0 AC 0
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
wrdata ../figures/psrrp.dat psrr
let psrrdc = psrr[0]
print psrrdc > ../sim/psrrp_dc.txt
quit
.endc
.end
