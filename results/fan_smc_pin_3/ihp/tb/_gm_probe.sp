.lib "../../../../models/pdk/ihp-sg13g2/ihp-sg13g2/libs.tech/ngspice/models/cornerMOSlv.lib" mos_tt
.include params.sp
.include dut.sp
.param VDD=1.2
.param VCM=0.6
VDD vdda 0 DC {VDD}
VSS gnda 0 DC 0
VINP vinp 0 DC {VCM} AC 0
VINN_DC vinn_dc 0 DC {VCM} AC 1
Lfb vout vinn 1k
Cfb vinn vinn_dc 1
Rbig vinn 0 1G
CL vout 0 {CLOAD}
Xdut gnda vdda vinn vinp vout fan_smc_pin_3
.control
set noaskquit
op
listing > ../sim/_listing.txt
show > ../sim/_show_all.txt
print all > ../sim/_all.txt
quit
.endc
.end
