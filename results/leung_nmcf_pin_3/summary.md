# leung_nmcf_pin_3 — spice-analyzer summary

**PDF:** `results/leung_nmcf_pin_3/report.pdf` (clickable TOC)
**Source path:** `Leung_NMCF_Pin_3` (seed params placeholder W=L=1 → fitted um sizing)

## Agentic models
- Host: Cursor; Model: Composer (slug unknown); skill `.agents/skills/spice-analyzer` (see `agent_provenance.md` / TA)

## Pass/fail (primary gates: sky130 TT)

| Metric | Hand | Sim | Gate | Result |
|--------|------|-----|------|--------|
| DC gain | 111.4 dB | 105.38 dB | +/-1 dB | **FAIL** |
| GBW | 332 kHz | 213 kHz | +/-5% | **FAIL** |
| PM | 81.8 deg | 88.1 deg | +/-5 deg | **FAIL** |
| Power | 1.019 mW (OP) | 1.019 mW | +/-5% | **PASS** |

## Coverage

| Backend | Nominal | Corners | MC | CMRR/PSRR/noise | F1-F10 |
|---------|---------|---------|----|-----------------|--------|
| cmos | yes | HARD-SKIP (no ff/ss) | LOT N=200 | yes | yes (F7 skip) |
| sky130 | yes | tt/ff/ss | HARD-SKIP mismatch; F8/F9 = CMOS LOT proxy | yes | yes |
| ihp | yes | mos_tt/ff/ss | HARD-SKIP mismatch; F8/F9 = CMOS LOT proxy | yes | yes |
| gf180 | yes (SCALE_WM=0.25) | typical/ff/ss | HARD-SKIP mismatch; F8/F9 = CMOS LOT proxy | yes | yes |

## Cross-backend nominal (sim)

| Backend | Adc (dB) | UGF | PM (deg) | P (mW) |
|---------|----------|-----|----------|--------|
| cmos | 111.16 | 366 kHz | 89.0 | 0.393 |
| sky130 | 105.38 | 213 kHz | 88.1 | 1.019 |
| ihp | 102.58 | 640 kHz | 81.4 | 0.605 |
| gf180 | 108.98 | 299 kHz | 85.9 | 1.775 |

## Top mismatches / notes

1. Hand GBW from gm1/C0 overestimates sky130 UGF (~56%) — parasitics / effective C0.
2. Hand A0 from OP-gds stage product ~6 dB above sim.
3. Hand PM ~6 deg below sim on sky130; reduced 3p1z vs BSIM. Sky130 CMRR only ~23 dB (poor matching / bias).

## Fit / recovery

- CMOS: raised C0 to 80p / C1=2p / CL=20p after negative-PM iterations.
- sky130: RL-adapted um sizes (gmf M 263→40), C0=20p — healthy first pass.
- ihp: VDD=1.2 V; after PM=-43 deg at C0=20p, recovered with C0=80p / C1=2p / CL=50p.
- gf180: C0=80p / C1=2p / CL=50p after first PM-negative pass; SCALE_WM=0.25.
