# fan_smc_pin_3 summary

Source path: `Fan_SMC_Pin_3`. Run id: `fan_smc_pin_3`. Date: 12 September 2026.

**PDF:** `results/fan_smc_pin_3/report.pdf`

## Nominal

| Backend | Adc (dB) | UGF (MHz) | PM (deg) | P (mW) | Vout (V) |
|---------|----------|-----------|----------|--------|----------|
| cmos | 91.93 | 128.72 | 89.2 | 0.846 | 0.900 |
| sky130 | 78.66 | 12.54 | 81.5 | 0.963 | 0.918 |
| ihp | 83.57 | 97.69 | 97.8 | 0.628 | 0.600 |
| gf180 | 74.74 | 3.21 | 89.3 | 1.441 | 1.661 |

## Primary gates (sky130)

| Metric | Hand | Sim | Result |
|--------|------|-----|--------|
| Adc | 89.60 dB | 78.66 dB | FAIL |
| GBW | 7.11 MHz | 12.54 MHz | FAIL |
| PM | 72.2 deg | 81.5 deg | FAIL |
| Power | 0.963 mW | 0.963 mW | PASS |

## Coverage

- Backends: cmos, sky130, ihp, gf180 (healthy OP/ACDC)
- Corners tt/ff/ss on open PDKs
- Extended: CMRR/PSRR/noise plots
- MC: cmos LOT N=200; open-PDK mismatch HARD-SKIP
- F1-F10 embedded (CMOS provides F8/F9)

## Top mismatches

1. sky130 hand GBW vs sim UGF (-43%; starved gm1)
2. sky130 hand PM vs sim (-9.3 deg)
3. gf180 hand A0/GBW over-predict sim

## Recovery

sky130: Ib=50uA, Cc=1pF, widened FETs from W=L=1u placeholders. IHP osdi spiceinit. GF180 fnoicor/sw_stat params.

## Agentic models

Cursor / Composer -- skill spice-analyzer (TA / agent_provenance.md).
