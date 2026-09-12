# IHP backend status — SUCCESS

Previously HARD-SKIPPED (PDK fetch incomplete). Now complete:

- PDK: `models/pdk/ihp-sg13g2/` with `cornerMOSlv.lib` + OpenVAF OSDI (`psp103*.osdi`)
- Nominal mos_tt ACDC + CMRR/PSRR/noise: OK (`metrics.json`)
- Corners mos_tt/ff/ss: OK (`corners.csv`)
- MC mismatch: HARD-SKIP → see `mc_hard_skip.md` (CMOS LOT proxy for F8/F9)
- Fit/recovery: `fit.md`, `recovery.md`
