---
name: spice-analyzer
description: Analyze analog SPICE netlists with small-signal hand analysis, run ngspice simulation, compare theory vs sim, and emit a LaTeX/PDF report under results/. Use when the user provides a netlist, asks for AC/small-signal analysis, amplifier validation, AnalogGym circuit checks, voltage-reference analysis, or spice-analyzer reports.
---

# Spice Analyzer

Validate an analog netlist: small-signal analysis → ngspice sim → theory-vs-sim comparison → LaTeX/PDF in `results/`.

## Scope (phased)

| Phase | Circuit class | Status |
|-------|---------------|--------|
| 1 | Amplifier (op-amp / OTA) | **Active** |
| 2 | Voltage reference | Planned |
| 3 | Other AnalogGym blocks (LDO, charge pump, PLL, SFE) | Later |

If the circuit is not an amplifier and phase support is missing, say so, still run what sims you can, and structure the report for future metrics.

## Inputs

Require from the user (ask only for what is missing):

1. **Netlist** path or pasted content (`.cir` / `.sp` / subckt file)
2. **Circuit class** (default: `amplifier`)
3. Optional: design-variables file, PDK/corner, supply, load, VCM, expected specs

Repo references:

- AnalogGym root: `tools/AnalogGym/AnalogGym/`
- Amp TB: `tools/AnalogGym/AnalogGym/Amplifier/amp_spice_testbench/TB_Amplifier_ACDC.cir`
- Amp netlists: `tools/AnalogGym/AnalogGym/Amplifier/spice_netlist/`
- Amp sizing: `tools/AnalogGym/AnalogGym/Amplifier/design_variables/`
- Amp metrics helper: `tools/AnalogGym/AnalogGym/Amplifier/perf_extraction_amp.py`
- Local PDK (if present): `models/pdk/`

Default simulator: **ngspice**. Prefer WSL on this machine if Windows `git`/tools are incomplete.

## Workflow

Copy and track:

```
Spice Analyzer Progress:
- [ ] 1. Ingest netlist
- [ ] 2. Small-signal analysis
- [ ] 3. Build / adapt testbench
- [ ] 4. Run simulation
- [ ] 5. Compare theory vs sim
- [ ] 6. Write LaTeX + PDF under results/
```

### 1. Ingest netlist

- Identify top-level `.subckt`, pin order, devices, passives, bias sources.
- Resolve `.include` / `.lib` / design variables; note PDK models (e.g. `sky130_fd_pr__*`).
- Infer topology (single-stage, two-stage Miller, multi-stage with FF/NF compensation, etc.).
- Record operating assumptions: `VDD`, `VSS`, `VCM`, `Cload`, temp, corner (`tt` default).

### 2. Small-signal analysis

Derive by hand (show equations in the report):

**Amplifier (phase 1)**

- Bias: estimate branch currents / inversion level when possible from W/L and TB bias.
- Stage gains: \(A_{v,i} \approx g_{m,i} R_{\mathrm{out},i}\)
- DC gain \(A_0\), dominant/non-dominant poles, zeros from compensation
- GBW \(\approx g_{m1}/(2\pi C_c)\) (adjust for topology)
- Phase margin estimate at unity-gain frequency
- Optional: CMRR / PSRR first-order estimates

**Voltage reference (phase 2 — stub)**

- \(V_{\mathrm{ref}}\) expression, TC, line sensitivity — expand when phase is active.

Document assumptions (which devices set \(g_m\), neglected parasitics, mid-band vs DC).

### 3. Build / adapt testbench

For amplifiers, start from `TB_Amplifier_ACDC.cir`:

- Point `.include` at the user netlist + design variables
- Instantiate correct subckt name and pin order: `gnda vdda vinn vinp vout`
- Keep ADM (unity-gain feedback AC), optional CMRR / PSRR / DC temp blocks
- Typical measures: `dcgain`, `gain_bandwidth_product`, `phase_in_deg`, `cmrrdc`, `DCPSRp`/`DCPSRn`, power, `vos25`

Write working deck under `results/<run_id>/tb/` (do not modify AnalogGym originals unless asked).

PDK include order of preference:

1. Path already in the user’s netlist/TB
2. AnalogGym sky130 corners under Amplifier `mosfet_model/` (if present)
3. `models/pdk/` in this repo

### 4. Run simulation

```bash
ngspice -b results/<run_id>/tb/<deck>.cir -o results/<run_id>/sim/ngspice.log
```

- Capture `.meas` results and key vectors (AC magnitude/phase).
- Export plots as PDF/PNG into `results/<run_id>/figures/` when possible (`gnuplot`/matplotlib).
- On failure: fix missing models, pin order, or DC convergence; re-run before reporting.

### 5. Compare theory vs sim

Build a comparison table for each metric:

| Metric | Hand / small-signal | Simulated | Rel. error | Match? |
|--------|---------------------|-----------|------------|--------|

Suggested match gates (amplifier, unless user overrides):

- DC gain: within **±3 dB**
- GBW: within **±30%**
- Phase margin: within **±10°**
- Bias / power: within **±30%** when estimated

Flag mismatches with likely causes (wrong stage identification, missing \(C_{gd}\), operating-region error, TB feedback setup).

### 6. LaTeX → PDF → `results/`

Create:

```
results/<run_id>/
  report.tex
  report.pdf
  tb/
  sim/
  figures/
  summary.md          # optional short mirror of findings
```

`<run_id>`: `<circuit_name>_<YYYYMMDD>_<HHMM>` or user-provided name.

Compile (prefer `latexmk`):

```bash
cd results/<run_id> && latexmk -pdf -interaction=nonstopmode report.tex
```

Fallback: `pdflatex -interaction=nonstopmode report.tex` (twice if refs).

Use the report skeleton in [reference.md](reference.md). Embed figures with relative paths. Keep equations via `amsmath`.

## Output to the user

After the PDF exists, reply with:

1. Path to `results/<run_id>/report.pdf`
2. Pass/fail vs match gates (bullet list)
3. Top 1–3 mismatch explanations if any

## Rules

- Prefer adapting AnalogGym TBs over inventing incompatible decks.
- Never claim match without both hand numbers and sim numbers.
- Do not commit results unless asked.
- Do not edit files under `tools/AnalogGym/` unless the user requests upstream changes; copy into `results/`.

## Additional resources

- Metrics, LaTeX skeleton, pin conventions: [reference.md](reference.md)
