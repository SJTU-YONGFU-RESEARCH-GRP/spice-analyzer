* smoke SE
.include /mnt/d/proj/voltage_reference_expt/models/opamp.lib
Vdd vdd 0 1.8
Vss vss 0 0
Vinp inp 0 0.901
Vinm inm 0 0.9
X1 inp inm out vdd vss opamp_se
.op
.control
run
print v(out) v(inp) v(inm)
.endc
.end
