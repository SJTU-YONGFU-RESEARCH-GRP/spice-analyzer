* temp probe
.include D:/proj/voltage_reference_expt/models/cmos.lib
Vdd vdd 0 1.8
Mp vref vref vdd vdd pmos_rvt W=4u L=0.36u
Mn vref vref 0 0 nmos_nat W=1u L=0.36u
.control
set filetype=ascii
foreach t -40 27 125
  set temp = $t
  op
  print v(vref)
end
.endc
.end
