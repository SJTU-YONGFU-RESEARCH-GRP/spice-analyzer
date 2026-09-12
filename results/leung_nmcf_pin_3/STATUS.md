# Spice Analyzer Progress — leung_nmcf_pin_3

- [x] 1. Ingest netlist
- [x] 2. Small-signal analysis (full algebra + TF how/why; anti-skip checklist)
- [x] 3a. Educational CMOS bench -- healthy OP + ACDC + plots data
- [x] 3. Build / adapt testbench (per open PDK: sky130 / ihp / gf180)
- [x] 3b. Fit / retarget sizing per PDK (if needed)
- [x] 4. Run simulation (healthy OP) -- nominal corner
- [x] 4b. Recover bias/sizing if OP collapsed or metrics missing
- [x] 4c. Corner sweep (tt/ff/ss unless opted out) + corner plots
- [x] 4d. Monte Carlo (N=200 mismatch unless opted out) + MC plots
- [x] 4e. Extended specs (CMRR, PSRR+/-, noise density+spots, vos) + plots
- [x] 5. Compare theory vs sim (re-derive from final OP; fill Hand|Sim|error)
- [x] 6. Write LaTeX + PDF (TOC + figures + **fully filled tables** + **agentic provenance TA**)
- [x] 6b. Pre-PDF audit: empty cells, TF derivation depth, anti-skip, **TA filled**

## Hard-skips
- sky130/ihp/gf180 mismatch MC: non-physical in this flow; CMOS LOT proxy for F8/F9
- cmos corners: no foundry ff/ss
