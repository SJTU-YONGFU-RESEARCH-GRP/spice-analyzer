# CMOS fit / recovery log

## Seed
Placeholder W=L=1 collapsed expected; skipped direct seed sim on educational Level-1.

## Iterations
1. RL-fit um sizes, C0=5p C1=3p CL=100p gmf M=40 → mid-rail OP, Adc~146 dB, UGF~8 MHz, **PM negative** (fp2 below UGF).
2. C0=50p / C1=2p / gmf M=60 → still PM negative.
3. Reduced gm1, Ib=5u, C0=20p C1=4p CL=50p → still PM negative.
4. **Final:** C0=80p, C1=2p, CL=20p, Ib=5u, moderate devices, gmf M=16 → healthy:
   - Vout ≈ 0.90 V (mid-rail)
   - Adc ≈ 111.2 dB
   - UGF ≈ 366 kHz
   - PM ≈ 89.0° (VINN-drive, `pm_deg = phase_at_ugf`)
   - I(VDD) ≈ see metrics; gm1≈184 µS, gm2≈296 µS, gm3≈285 µS, gmf≈117 µS

## Notes
- Educational Level-1 only; not process-qualified.
- Noise spot `meas` after `setplot noise1` failed (ngspice plot context); density curve still written.
- No foundry ff/ss on cmos; LOT MC via `.param mc=1`.
