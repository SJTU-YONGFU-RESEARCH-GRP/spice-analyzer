* fan_smc_pin_3 ACDC (ihp)


.lib '../../../../models/pdk/ihp-sg13g2/ihp-sg13g2/libs.tech/ngspice/models/cornerMOSlv.lib' mos_ff

.include params.sp
.include dut.sp

.param VDD=1.2
.param VCM=0.6

VDD vdda 0 DC {VDD}
VSS gnda 0 DC 0
* Common-mode bias on VINP; VINN AC-driven (inverting drive => LF phase ~180)
VINP vinp 0 DC {VCM} AC 0
VINN_DC vinn_dc 0 DC {VCM} AC 1
* DC unity-gain feedback: vout -> vinn through big L (AC open)
Lfb vout vinn 1k
Cfb vinn vinn_dc 1
Rbig vinn 0 1G
CL vout 0 {CLOAD}

Xdut gnda vdda vinn vinp vout fan_smc_pin_3

.control
set noaskquit
set filetype=ascii
op
let idd_op = -i(VDD)
let vout_op = v(vout)
let power_op = idd_op * 1.2
print idd_op > ../sim/idd.txt
print vout_op > ../sim/vout_dc.txt
print power_op > ../sim/power.txt
print all > ../sim/op_nodes.txt
show m > ../sim/op_devices.txt

* Explicit gm/gds capture (works for BSIM/PSP when show-m is sparse)
let gm_m8 = @m.xdut.xm8[gm]
let gm_m9 = @m.xdut.xm9[gm]
let gm_m10 = @m.xdut.xm10[gm]
let gm_m11 = @m.xdut.xm11[gm]
let gm_m23 = @m.xdut.xm23[gm]
let gds_m8 = @m.xdut.xm8[gds]
let gds_m10 = @m.xdut.xm10[gds]
let gds_m23 = @m.xdut.xm23[gds]
let gds_m11 = @m.xdut.xm11[gds]
let id_m8 = @m.xdut.xm8[id]
let id_m10 = @m.xdut.xm10[id]
let id_m23 = @m.xdut.xm23[id]
let id_m11 = @m.xdut.xm11[id]
print gm_m8 > ../sim/gm_m8.txt
print gm_m9 > ../sim/gm_m9.txt
print gm_m10 > ../sim/gm_m10.txt
print gm_m11 > ../sim/gm_m11.txt
print gm_m23 > ../sim/gm_m23.txt
print gds_m8 > ../sim/gds_m8.txt
print gds_m10 > ../sim/gds_m10.txt
print gds_m23 > ../sim/gds_m23.txt
print gds_m11 > ../sim/gds_m11.txt
print id_m8 > ../sim/id_m8.txt
print id_m10 > ../sim/id_m10.txt
print id_m23 > ../sim/id_m23.txt
print id_m11 > ../sim/id_m11.txt

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
