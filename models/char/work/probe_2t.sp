* probe 2T topologies
.include D:/proj/voltage_reference_expt/models/cmos.lib
.temp 27

* --- A: PMOS diode + NMOS diode (nat) ---
Vdda vdda 0 1.8
Mpa vrefa vrefa vdda vdda pmos_rvt W=4u L=0.36u
Mna vrefa vrefa 0 0 nmos_nat W=1u L=0.36u

* --- B: PMOS gate-gnd current source + HVT diode ---
Vddb vddb 0 1.8
Mpb vrefb 0 vddb vddb pmos_rvt W=2u L=0.36u
Mnb vrefb vrefb 0 0 nmos_hvt W=4u L=0.36u

* --- C: RVT PMOS diode + HVT NMOS diode ---
Vddc vddc 0 1.8
Mpc vrefc vrefc vddc vddc pmos_rvt W=2u L=0.36u
Mnc vrefc vrefc 0 0 nmos_hvt W=2u L=0.36u

.control
set filetype=ascii
op
print v(vrefa) v(vrefb) v(vrefc)
.endc
.end
