# IHP fit

Start: sky130 fitted W/L/M converted to meters; VDD=1.2 V, VCM=0.6 V,
C0=20p, C1=3p, CL=100p, Ib=10u.

Iter0: healthy OP (Vout≈0.600 V) but PM=-43 deg, UGF≈2.60 MHz (gm1≈9× sky130).

Iter1 recovery: C0=80p, C1=2p, CL=50p (same compensation strategy as gf180).
Result: Adc=102.58 dB, UGF=640 kHz, PM=81.4 deg, P=0.605 mW (TB i(VDD)×VDD).
CMRR≈62.5 dB, PSRR+≈61.7 dB, PSRR-≈81.9 dB.

Final params in `ihp/tb/params.spice`. Devices: `sg13_lv_nmos` / `sg13_lv_pmos`
via `.lib cornerMOSlv.lib mos_tt|mos_ff|mos_ss`. OSDI compiled with openvaf
(psp103*.osdi).
