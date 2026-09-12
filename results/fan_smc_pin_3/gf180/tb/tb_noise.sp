* Input-referred noise (gf180)
.param fnoicor=0
.param sw_stat_mismatch=0
.param sw_stat_global=0
.param sw_stat_local=0


.lib '../../../../models/pdk/gf180mcu_fd_pr/models/ngspice/sm141064.ngspice' typical

.include params.sp
.include dut.sp
.param VDD=3.3
.param VCM=1.65
VDD vdda 0 DC {VDD}
VSS gnda 0 DC 0
VINP vinp 0 DC {VCM} AC 0
VINN_DC vinn_dc 0 DC {VCM} AC 0
Lfb vout vinn 1k
Cfb vinn vinn_dc 1
Rbig vinn 0 1G
CL vout 0 {CLOAD}
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
