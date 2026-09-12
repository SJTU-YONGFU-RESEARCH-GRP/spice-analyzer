* fan_smc_pin_3 ACDC (cmos)


.include '../../../../models/cmos.lib'
.param mc=1

.include params.sp
.include dut.sp

.param VDD=1.8
.param VCM=0.9

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
setseed 42
echo trial,ugf_Hz,pm_deg,adc_dB > ../sim/mc_results.csv
let i = 1
dowhile i <= 200
  reset
  op
  ac dec 40 1 1G
  let mag = db(v(vout))
  let ph = 180/pi*ph(v(vout))
  let adc = mag[0]
  let ugf = 0
  let ph_ugf = 0
  let found = 0
  let npts = length(frequency)-1
  let k = 0
  dowhile k < npts
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
  if found = 1
    if ph_ugf < 0
      let pmv = 180 + ph_ugf
    else
      let pmv = ph_ugf
    end
    echo $&i,$&ugf,$&pmv,$&adc >> ../sim/mc_results.csv
  else
    echo $&i,nan,nan,$&adc >> ../sim/mc_results.csv
  end
  let i = i + 1
end
quit
.endc
.end
