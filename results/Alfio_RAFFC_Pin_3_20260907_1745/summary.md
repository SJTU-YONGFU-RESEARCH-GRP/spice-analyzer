# Alfio_RAFFC_Pin_3 — summary

- **Topology:** 3-stage RAFFC (PMOS input folded cascode → PMOS CS → PMOS CS + FF), Cc=11p / 0.35p, CL=100p, Ibias=20µA, sky130 tt.
- **Hand (ideal sat.):** gm1≈45–200 µS → GBW≈0.65–2.9 MHz; A0∼60–100 dB.
- **Sim (stock W=L=1 sizing):** ADM DC gain **−15.3 dB**, no 0 dB crossing; Power 0.326 mW; Vos −214 mV. OP railed (vout≈29 mV).
- **Match gates:** FAIL (gain / GBW / PM). Root cause: AnalogGym placeholder sizing, not a biased amplifier.
- **PDF:** `results/Alfio_RAFFC_Pin_3_20260907_1745/report.pdf`
