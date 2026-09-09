---
name: spice-analyzer
description: Analyze analog SPICE netlists (any origin -- user paste, local file, benchmark suite, or foundry deck) with step-by-step small-signal hand analysis (no skipped algebra; TF Steps 4.0--4.4 with per-node KCL/Miller in 4.3; mandatory Hand tables T1--T5 mirrored from algebra), fully filled report tables T0--T10, multi-PDK ngspice benches (cmos then sky130 / IHP SG13G2 / GF180 by default), corners and Monte Carlo, mandatory CMRR/PSRR/noise/corner/MC plots, hand-vs-sim Bode overlays, clickable TOC LaTeX/PDF reports under results/. Use when the user provides a netlist, asks for AC/small-signal analysis, amplifier validation, PDK fitting/benching, corner/MC sweeps, or spice-analyzer reports.
---

# Spice Analyzer

Validate an analog netlist: **full** small-signal derivation -> educational `cmos.lib` smoke -> **every open PDK present** (sky130 / IHP / GF180) with **corners** + **MC** -> full amp specs with **embedded plots** -> theory-vs-sim -> LaTeX/PDF with **clickable TOC** under `results/`.

**Do not stop early.** A PDF that only documents a collapsed bias / placeholder sizing / failed match is incomplete unless recovery was attempted and hard-blocked (see §4b and Definition of done).

**Do not skip intermediate algebra.** Listing Steps 0--8 as headings with final numbers only is a fail -- see §2 Anti-skip / acceptance.

**Do not leave tables half-empty.** Every required metrics / corner / MC / match cell must hold a number **or** an explicit typed reason (e.g. `no hand model`, `HARD-SKIP: …`) -- bare `---`, blank cells, or `TBD` are a fail. See §6 Table completeness. **T1--T5 are mandatory:** Hand numbers that appear in §2 equations must be copied into those tables (equations-only is a fail).

**Do not drop pole/zero formulas without derivation.** Step 4 must explain **how** and **why** \(A(s)\) is obtained (signal path, small-signal model, **per-node KCL or Miller equations in 4.3**, which approximation yields each \(\omega_{p,k},\omega_z\)) before quoting the reduced TF -- see §2 Step 4 substeps. A topology name + final 3p1z line is not enough.

## Scope (phased)

| Phase | Circuit class | Status |
|-------|---------------|--------|
| 1 | Amplifier (op-amp / OTA) | **Active** |
| 2 | Voltage reference | Planned |
| 3 | Other blocks (LDO, charge pump, PLL, sensors, ...) | Later |

If the circuit is not an amplifier and phase support is missing, say so, still run what sims you can, and structure the report for future metrics.

## Inputs

**Source-agnostic (hard rule):** the DUT may come from anywhere (pasted text, local path, paper supplement, foundry IP, or an in-repo file under any folder). Analyze the **netlist contents**, not the hosting suite.

**Do not brand datasets or platforms** in reports, TOC titles, figure captions, chat summaries, or skill-facing prose. Forbidden as narrative labels (examples, not exhaustive): AnalogGym, AmpGym, OpenCircuitDesign suites, foundry "PDK demo kit" names, contest/benchmark suite names, course-lab branding. Same rule for **any future** dataset dropped under `tools/` or elsewhere.

Allowed:

- One verbatim **source path** or "user-provided paste" in Circuit under test / Appendix.
- Technical facts from the file (`.subckt` name, pins, Spectre/SPICE port notes, original \(V_{DD}\)).

Not allowed:

- Framing the run as an "\<Suite\> analysis / check / port."
- Section titles like "AnalogGym netlist," "seeds from \<Suite\>."
- Preferring a suite TB over a user TB, or assuming suite pin templates.

Require from the user (ask only for what is missing):

1. **Netlist** path or pasted content (`.cir` / `.sp` / subckt file)
2. **Circuit class** (default: `amplifier`)
3. Optional: design-variables / parameters file, supply, load, common-mode bias, expected specs, existing testbench
4. Optional **backend / PDK set** (default pipeline below). Tokens: `cmos`, `sky130`, `ihp`, `gf180`, `all` (= all open PDKs present under `models/pdk/`), `pdk_only`, `cmos_only`.
5. Optional **corners** (default on each open/commercial PDK: **`tt,ff,ss`** / vendor `typical`+`ff`+`ss`). Opt out: `no_corners` / `tt` only / `all_corners`. On `cmos`: educational LOT/`mc` only -- do **not** invent foundry ff/ss for Level-1.
6. Optional **MC** (default: **on**, **N=200**, **`mismatch`** on PDKs; on `cmos` use `.param mc=1` LOT). Ask before N>200. Opt out: `no_mc` / `MC off`. Hard-skip with reason if unsupported -- do not invent statistics.

**Default backend order (amplifiers):**

1. **`cmos`** -- remap to `nmos_rvt`/`pmos_rvt` (or documented Vt flavors) via `models/cmos.lib`. Label **educational / not process-qualified**.
2. **All open PDKs present** under `models/pdk/` among **`sky130`**, **`ihp`**, **`gf180`** (skip a token only if the tree is missing -- log hard-skip + how to `fetch.sh`). If the netlist implies one process, still run the others when present unless the user said e.g. `sky130_only`. Fit sizing **per PDK** (§3b). Never claim PDK match from `cmos` alone.

User shortcuts: `sky130_only` / `ihp_only` / `gf180_only` / named list override the "all present" default.

Tooling defaults:

- Simulator: **ngspice** (batch); Windows: WSL or portable/conda `ngspice_con` (IHP needs **>=41** + OSDI)
- Reports under **one** `results/<run_id>/` (see single-folder rule in §3)
- Models: `models/cmos.lib`, `models/pdk/` -- see [reference.md](reference.md)

## Workflow

Copy and track (keep boxes unchecked until that stage is *actually* done):

```
Spice Analyzer Progress:
- [ ] 1. Ingest netlist
- [ ] 2. Small-signal analysis (full algebra + TF how/why; anti-skip checklist)
- [ ] 3a. Educational CMOS bench -- healthy OP + ACDC + plots data
- [ ] 3. Build / adapt testbench (per open PDK: sky130 / ihp / gf180)
- [ ] 3b. Fit / retarget sizing per PDK (if needed)
- [ ] 4. Run simulation (healthy OP) -- nominal corner
- [ ] 4b. Recover bias/sizing if OP collapsed or metrics missing
- [ ] 4c. Corner sweep (tt/ff/ss unless opted out) + corner plots
- [ ] 4d. Monte Carlo (N=200 mismatch unless opted out) + MC plots
- [ ] 4e. Extended specs (CMRR, PSRR+/-, noise density+spots, vos) + plots
- [ ] 5. Compare theory vs sim (re-derive from final OP; fill Hand|Sim|error)
- [ ] 6. Write LaTeX + PDF (TOC + figures + **fully filled tables**)
- [ ] 6b. Pre-PDF audit: empty cells, TF derivation depth, anti-skip
```

### 1. Ingest netlist

- Identify top-level `.subckt` (or top circuit), **pin order**, devices, passives, bias sources.
- Resolve `.include` / `.lib` / parameter files; note source PDK/device models.
- Record provenance as a **path or paste** only -- do not label the circuit by dataset/suite name (see Inputs hard rule).
- Snapshot the DUT (+ params) into `results/<run_id>/` before editing.
- Infer topology (single-stage, two-stage Miller, multi-stage with FF/NF compensation, bandgap, ...).
- Record operating assumptions: `VDD`, `VSS`, input CM, `Cload`, temperature, corner (nominal `tt` / `typical` first).
- **Flag seed / placeholder sizing** (e.g. all `W=L=1`, Spectre `1u` stubs) -- §3b / §4b, not a finished design.
- Choose backends: **`cmos` + every present open PDK** unless user narrowed the set; verify each tree before promising it.

### 2. Small-signal analysis

**Required:** LaTeX must contain a **step-by-step derivation** with **numbered steps**, **equations**, **intermediate substituted arithmetic**, then a **final number**. Jumping to GBW/PM one-liners is not enough. **Power Steps 7.1--7.5 are mandatory.** **Transfer-function Steps 4.0--4.4 are mandatory** (how/why, not formula dump).

**Tables are part of the derivation (hard rule):** every Hand number used later for match / Bode overlay / PM **must also appear in the corresponding §2 table (T1--T5)**. Equations-only algebra with empty or missing T1--T5 is a **fail** -- agents have repeatedly left Hand columns blank while the math lived only in `align` environments. Prose/equations **and** tables are both required; tables are not optional summaries.

Write hand analysis primarily for the **primary foundry PDK** used for match gates (usually first healthy open PDK, often sky130); note CMOS Level-1 differences in a short aside. After recovery, **refresh Steps 1--8 from final OP** \(I_D\)/\(g_m\) (do not leave only pre-sim seed estimates). On **secondary** healthy backends, either re-derive briefly from local OP \(g_m\)/\(g_{ds}\) **or** scale the primary RAFFC/Miller formulas with OP-\(g_m\) + same caps and **still fill T6 Hand** for \(A_0\), GBW, PM, \(P\) -- do **not** write `no hand model` for those core rows when a TF model exists.

**Pedagogy bar:** a reader who knows MOSFET small-signal models but not this schematic must be able to reproduce \(A(s)\) and the numeric GBW/PM from the report alone -- no "by inspection" or "standard RAFFC formulas" without a short derivation trail. Prefer **more** intermediate lines over fewer: each mirror ratio, each \(r_o\parallel r_o\), each \(\tan^{-1}\) argument.

#### Amplifier (phase 1) -- mandatory step sequence

| Step | Content (must show algebra + plugged numbers **and** table where noted) |
|------|-----------------------------------------------|
| **0. Assumptions** | Inversion level, \(\mu C_{\mathrm{ox}}\) / \(V_{\mathrm{ov}}\) (or OP-based), neglected parasitics, saturation caveat, which PDK/\(V_{DD}\)/sizing the hand numbers use |
| **1. Bias currents** | From \(I_b\) and every mirror \(M\): \(I_{\mathrm{tail}}\), per-stage / FF / bias-branch \(I_{D,i}\). **Show \(I_k = M_k/M_{\mathrm{ref}}\cdot I_b\) lines for every branch cited.** Then list sim OP \(I_D\) beside hand. **Mandatory T1** (device / hand \(I_D\) / OP \(I_D\) / note). OP-assisted rows allowed if labeled. |
| **2. Transconductances** | For **each** signal device (\(g_{m1},g_{m2},\ldots,g_{mf}\)): show square-law and/or \(2I_D/V_{\mathrm{ov}}\) **with numeric \(W,L,M,I_D,\mu C_{\mathrm{ox}}\) or \(V_{\mathrm{ov}}\)** -- **full arithmetic for every distinct \(g_m\) role**, not one example plus "similarly". Then **quote sim OP \(g_m\)** and use OP \(g_m\) for later steps once healthy. **Mandatory T2** (device / hand \(g_m\) / OP \(g_m\)). |
| **3. Stage \(R_{\mathrm{out}}\) and gains** | Per stage: start from OP \(g_{ds}\) (or \(\lambda I_D\)); show \(r_o=1/g_{ds}\); then \(R_{\mathrm{out},i}=r_{o,\mathrm{drv}}\parallel r_{o,\mathrm{load}}\) **with both operands numeric** (cascode: expand \(g_m r_o r_o\) with substituted numbers before the parallel). \(A_{v,i}=g_{m,i}R_{\mathrm{out},i}\) **with numbers**. \(A_0=\prod A_{v,i}\) (and FF path note) -> **dB**. **Mandatory T3** (stage / \(R_{\mathrm{out}}\) / \(A_v\) lin / \(A_v\) dB). Never jump from OP \(g_m\) to measured \(A_0\). |
| **4. Compensation / TF** | Substeps **4.0--4.4** below -- never only the final \(A(s)\) line. **4.3 must show nodal KCL or Miller reduction with intermediate equations** (see detail). |
| **5. GBW and non-dominant poles** | Substitute into \(\mathrm{GBW}\) and each \(f_{p,k}\), \(f_{z,j}\) -- **one equation line -> one numeric line** each. **Mandatory T4** (symbol / formula / Hand Hz / Sim Hz or `n/a (hand TF)`). |
| **6. Phase margin** | \(\mathrm{PM}\approx 90^\circ-\sum\tan^{-1}(\omega_t/\omega_{p,k})+\sum\tan^{-1}(\omega_t/\omega_{z,j})\) (or topology-specific). **Show each \(\tan^{-1}\) argument (\(\omega_t/\omega\)) and degree value**, then the sum. Prefer a small **PM term table**. State TB phase convention (VINN-drive vs non-inv). |
| **7. Power** | Substeps **7.1--7.5** below -- never a lone \(P=V_{DD}I_{DD}\). **Mandatory T5** branch map + Hand\|Sim compare table in 7.5. |
| **8. FoM** | At least \(\mathrm{FOM}_S=\mathrm{GBW}\cdot C_L/P\) with numbers; add \(\mathrm{FOM}_L\) if SR exists. |

**Step 4 detail (transfer function -- how and why):**

| Substep | Content |
|---------|---------|
| **4.0 Signal path** | Name topology (Miller / NMC / RNMC / RAFFC / AFFC / telescopic / folded / …). Prose: which devices form stage 1/2/3/FF; which nodes are \(v_1,v_2,v_{\mathrm{out}}\); where each compensation cap attaches (**net names from the netlist**). |
| **4.1 Small-signal model** | List the controlled sources and caps retained (\(g_{m1},g_{m2},\ldots\), \(r_{o}\) lumps or \(R_1,R_2,\ldots\), \(C_c,C_a,C_L,\ldots\)). State what is neglected (device \(C_{gs}/C_{gd}\), interconnect) and why that is acceptable for the target GBW band. Name every node kept in the model. |
| **4.2 Why each singularity** | For **every** pole and zero kept in the reduced model: one short physical/algebraic reason tied to **this** netlist (not a generic slogan). **Forbidden:** "using standard formulas" / "by inspection" with no reason line. |
| **4.3 Derive reduced \(A(s)\)** | **Minimum depth (all required):** (1) write KCL (or explicit Miller/loop equations) at **each** retained node \(v_1,v_2,\ldots,v_{\mathrm{out}}\) with the controlled sources and caps from 4.1; (2) state high-gain / integrator / neglect-\(s^2\) approximations **as separate lines** with justification; (3) reduce to the rational \(A(s)\) used later. A topology name + final 3p1z formula **without** node equations is a **fail**. Paper citation only as backup after the in-report derivation. Worked sketches: [reference.md](reference.md). |
| **4.4 Named formulas** | Give the **symbolic** expression for each \(\omega_{p,k},\omega_z,\omega_t\) **before** Step 5 numbers (match `hand_tf_params.txt` keys). |

**Step 7 detail:**

| Substep | Content |
|---------|---------|
| **7.1 Branch map** | **T5 table:** every DC path \(V_{DD}\to V_{SS}\) with device names |
| **7.2 Ideal hand currents** | Each \(I_k\) from \(I_b,M\); \(I_{DD,\mathrm{hand}}=\sum I_k\) with arithmetic (include stage-2/3/FF -- do not stop at bias-only) |
| **7.3 Hand power** | \(P_{\mathrm{hand}}=V_{DD}\cdot I_{DD,\mathrm{hand}}\) (show ideal and OP-assisted if they differ) |
| **7.4 Sim OP** | Key \(I_D\) + \(I(V_{DD})\); \(P_{\mathrm{sim}}\) |
| **7.5 Compare** | Table: Hand \| Sim \| Rel. error \| Match? vs +/-5%; explain missing branches / triode |

#### Anti-skip / acceptance (agent self-check before PDF)

A step **fails** if any of these hold:
...
- T6/T10 **Match?** column missing, clipped, or filled with `n/a` for core \(A_0\)/GBW/PM/\(P\) rows that have numeric Hand and Sim (must be PASS or FAIL vs gates)

- Final number appears with **no** preceding substituted equation for that quantity
- Hand / OP numbers exist in `align` but **T1--T5 (as applicable) are missing or lack Hand columns**
- Step 2 shows arithmetic for only one \(g_m\) and waves hands at the others ("similarly", "same order")
- Step 2 says "same order" / "agrees with OP" without fully numeric square-law or \(2I_D/V_{\mathrm{ov}}\) per distinct \(g_m\) role
- Step 3 has no numeric \(R_{\mathrm{out},i}\) and \(A_{v,i}\) (hand-wavy "\(g_m r_o\) order-of-magnitude" alone is insufficient unless \(r_o\)/\(g_{ds}\) were unavailable -- then state hard-limit and use OP `gds` from `.op`). Jumping from OP \(g_m\) straight to measured \(A_0\) **without** a per-stage \(R_{\mathrm{out}}\) trail fails
- Step 3 cascode / parallel combination written as a single result without showing the substituted factors
- Step 4 is only a named topology + final \(A(s)\) / pole list with **no** 4.0--4.4 trail, or 4.3 lacks **per-node KCL / Miller equations** before the reduced TF
- Step 4 names caps but does not define each pole/zero symbol
- Step 5/6 give GBW/PM without T4 and without term-by-term \(\tan^{-1}\) (arguments + degrees)
- Step 6 jumps to a PM number without term-by-term \(\tan^{-1}\)
- Step 7.2 omits output/FF branches that carry significant current in OP
- T6 Hand column says `no hand model` for \(A_0\) / GBW / PM / \(P\) on a backend that has a usable §2 TF or OP-\(g_m\) scaling (reserve `no hand model` for CMRR/PSRR/noise/offset unless those were derived)
- T6/T10 **Match?** column is missing, visually clipped, or set to `n/a` for core \(A_0\)/GBW/PM/\(P\) rows that already have numeric Hand and Sim (must be `PASS` or `FAIL` vs gates; put long notes under the table so Match? stays on-page)

Topology notes: Miller RHP zero; NMC/RNMC/RAFFC/AFFC -- name inner vs outer caps and buffered loops; folded/telescopic -- include \(g_{mb}\) in \(R_{\mathrm{out},1}\). Detail recipes + worked TF sketches: [reference.md](reference.md) -- Hand-analysis depth.

**Voltage reference (phase 2 -- stub):** \(V_{\mathrm{ref}}\), TC, line sensitivity -- same no-skip algebra rule when active.

### 3. Build / adapt testbench

Write decks under `results/<run_id>/` (snapshot DUT + params). Prefer a user-supplied TB if given; else build a minimal ACDC bench matched to the DUT pins.

**Single main result folder (hard rule):**

- One analysis = **one** directory `results/<run_id>/`. Prefer a stable id from the DUT name (e.g. `alfio_raffc_pin_3`), not a new timestamped sibling on every retry.
- Do **not** leave parallel `results/<name>_YYYYMMDD[_HHMM]/` (or similar) folders for the same DUT. Intermediate attempts stay **inside** the main folder (overwrite `tb/`/`sim/`/`figures/`, or use a short-lived `scratch/` that is deleted before delivery).
- If an earlier partial run already exists under a different path and the PDF / figures / decks still need any of those files: **merge** them into the main `results/<run_id>/` (copy missing unique artifacts), rewrite all path references in `report.tex` / `summary.md` / scripts to the main folder, then **delete** the leftover timestamped / duplicate folders (and any restore manifests that resurrect them).
- Cite only `results/<run_id>/...` in the PDF, summary, and chat wrap-up.

```
results/<run_id>/
  report.tex / report.pdf / summary.md
  cmos/{tb,sim,figures}/
  sky130/{tb,sim,figures}/   # when present / requested
  ihp/{tb,sim,figures}/
  gf180/{tb,sim,figures}/
```

Each `figures/` must hold plot **data** (`.dat`/`.csv`) **and** renderable figures.

**Plot style (required):** use the skill-bundled **dev-plot** palette under `.agents/skills/spice-analyzer/plotting/` (MATLAB-aligned `#0033cc`/`#cc0000`/`#7f3fbf`, full spines, bold sans). Typography and linewidths must match **column-embed** constants in `plotting/plot_style.py` (title/label/tick ≈ 10/9/8, line ≈ 2.2/1.8, figsize ≈ 4.5×2.8–3.0 in) -- not the wide-dashboard 17/13/10 + line-7 sizes. **Do not** use `tools/plotting/` -- all plot commands point at the skill `plotting/` folder. Prefer Python renderers; keep `.ps1` fallbacks in sync.

```bash
# Preferred when Python+matplotlib available (Unix / Windows):
python3 .agents/skills/spice-analyzer/plotting/render_spice_figures.py results/<run_id>
python3 .agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.py results/<run_id>
bash .agents/skills/spice-analyzer/plotting/render_all.sh results/<run_id>          # Unix one-shot

# Windows one-shot (Python if present, else System.Drawing .ps1):
powershell -File .agents/skills/spice-analyzer/plotting/render_all.ps1 -RunDir results/<run_id>

# Windows fallbacks (no matplotlib):
powershell -File .agents/skills/spice-analyzer/plotting/render_spice_figures.ps1 -RunDir results/<run_id>
powershell -File .agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.ps1 -RunDir results/<run_id>
```

Embed **PNG** (and SVG when available) via `\includegraphics` -- do not rely on pgfplots alone on older MiKTeX. After compile, **open the PDF and confirm curves are visible**.

### 3a. Educational CMOS first

Unless `pdk_only`: remap -> `models/cmos.lib`; fix pin order/bias/compensation before PDK burn-in; label educational; include CMRR/PSRR/noise data when cheap.

### 3b. Fit / retarget sizing (per PDK)

Process-aware \(W/L/M\), \(V_{CM}\), \(I_b\) so each PDK reaches healthy OP + measurable GBW/PM. Log `sim/fit.md` / `recovery.md`. Smoke (same um everywhere) allowed only if labeled smoke -- not for match gates.

### 4--4b. Nominal sim + recovery

Batch ngspice; healthy OP checks (mid-rail out, mirrors alive, \(A_0\gg 0\,\mathrm{dB}\), UGF exists). On failure -> §4b loop (~few iters/PDK). Re-derive hand after recovery.

### 4c. Corners (default)

`tt/typical` + `ff` + `ss` per open PDK. Table **and** bar/grouped plot of gain / GBW / PM / power. Mark FAIL/no-UGF explicitly.

### 4d. Monte Carlo (default)

N=200 mismatch (unless opted out). CSV + `mc_summary.md` + **histograms (GBW and PM at least)** embedded in PDF. Hard-skip with reason if randomization unsupported.

### 4e. Extended specs (default)

| Spec | Minimum | **Must plot** |
|------|---------|----------------|
| CMRR | DC (dB) | \(\mathrm{CMRR}(f)\) (not DC-only when AC sweep exists) |
| PSRR+ **and** PSRR- | DC (dB) | both vs frequency |
| Noise | \(e_n\) @ 1 kHz **and** 1 MHz | density \(e_n(f)\) |
| Offset | unity-gain \(V_{\mathrm{os}}\) | -- |
| Slew / settle | if transient TB | \(v_{\mathrm{out}}(t)\) preferred |

Hard-skip a **plot** only with a one-line reason in the PDF (and still report any scalar you have, e.g. integrated noise).

### 5. Compare theory vs sim

Per-backend tables: Hand | Sim | Rel. error | Match?

Gates (unless overridden): DC gain **+/-1 dB**; GBW **+/-5%**; PM **+/-5 deg**; bias/power **+/-5%** when estimated.

**Fill rules for Hand | error | Match? columns:**

| Metric class | Hand column | Rel. error / Match? |
|--------------|-------------|---------------------|
| Core match-gated (\(A_0\), GBW/UGF, PM, \(P\)) | Numeric Hand from §2 or OP-\(g_m\) scale on **every** healthy backend (short number in the cell; put long notes under the table) | **Always** `PASS` or `FAIL` vs default gates (\(\pm1\,\mathrm{dB}\), \(\pm5\%\), \(\pm5^\circ\), \(\pm5\%\)) when Hand and Sim are both numeric -- **never** leave Match? as bare `n/a` for these rows. Primary PDK is the official gate table (T10); secondary backends still show PASS/FAIL for readability (footnote if not official). **FAIL is OK and expected** often: reduced hand TF vs BSIM/PDK (parasitics, \(\lambda\)/ \(g_{ds}\), compressed mirrors) rarely hits every gate -- still print FAIL, do not soften to `n/a` or skip Match?. A secondary FAIL does **not** by itself abort the run or force endless recovery if OP is healthy and primary gates were attempted. |
| Extended (CMRR, PSRR+/-, \(e_n\), \(V_{\mathrm{os}}\)) | Hand estimate if derived; else literal `no hand model` | Rel. error `n/a`; Match? `n/a` only when Hand is `no hand model` |
| Hard-skipped backend / corner / MC | Cell text `HARD-SKIP: <one-line reason>` | Do not leave blank |

**Match? visibility (LaTeX):** keep Hand cells short (numbers + units only). Put derivation notes in a `\footnotesize` line under the table. Prefer `{\small\begin{tabular}{@{}lrrrl@{}}...}` so the Match? column is not clipped off the right margin. Header text must be exactly `Match?` (or `Match` + footnote) -- do not omit the column.

Cross-backend summary table required when >=2 backends ran. Do not end on first FAIL while an obvious theory/TB error remains.

### 6. LaTeX -> PDF -> `results/`

**Required PDF features:**

1. **Clickable table of contents** -- `\usepackage{hyperref}` + `\tableofcontents` after `\maketitle` (run pdflatex/latexmk **twice**). Use `\section`/`\subsection` (not only `\subsection*`) so TOC entries and links work. Optional: `\usepackage{bookmark}`.
2. **All mandatory figures embedded** with captions and backend labels (see checklist below).
3. Full §2 derivation with anti-skip compliance (**including Steps 4.0--4.4**).
4. Per-PDK results sections (cmos, sky130, ihp, gf180 as applicable) + corners/MC + match assessment.
5. **All required tables present and fully filled** (see Table completeness below).

Compile: `latexmk -pdf` or `pdflatex` **twice**. Skeleton: [reference.md](reference.md) -- LaTeX report skeleton.

#### Mandatory figure checklist (amplifiers)

For **each** healthy backend (at least nominal), embed unless hard-skipped:

| ID | Figure |
|----|--------|
| F1 | Bode magnitude -- **sim + hand TF overlay** (required when §2 poles/zeros exist) |
| F2 | Bode phase -- **sim + hand TF overlay** (same TF; note VINN-drive +180 deg if used) |
| F3 | CMRR vs frequency |
| F4 | PSRR+ vs frequency |
| F5 | PSRR- vs frequency |
| F6 | Input-referred noise density (+ mark 1 kHz / 1 MHz spots) |
| F7 | Corner comparison (gain, GBW, PM, power) -- per open PDK that ran §4c |
| F8 | MC histogram/box -- GBW |
| F9 | MC histogram/box -- PM |
| F10 | Cross-backend bar (gain/GBW/PM/power) when >=2 backends |

**F1/F2 hand overlay (required for amplifiers):** After nominal ACDC and §2, write `<backend>/sim/hand_tf_params.txt` from final OP \(g_m\) and compensation caps, generate theory curves, and embed **overlay** PNGs (not sim-only) in the PDF. **Blue = simulation, red = hand TF** (dev-plot). Prefer Python on all OSes; PowerShell is Windows fallback:

```bash
# Unix / macOS / WSL (preferred)
python3 .agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.py results/<run_id>
bash .agents/skills/spice-analyzer/plotting/render_all.sh results/<run_id>

# Windows
powershell -File .agents/skills/spice-analyzer/plotting/render_all.ps1 -RunDir results/<run_id>
# or: plot_bode_theory_overlay.ps1 if matplotlib unavailable
powershell -File .agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.ps1 -RunDir results/<run_id>
```

Hard-skip overlay only if the topology has no usable pole/zero model yet -- state that in the PDF; still embed sim-only F1/F2.

Prefer PDF/PNG in `figures/` with `\includegraphics` (verify curves visible in the PDF). Render with `.agents/skills/spice-analyzer/plotting/render_spice_figures.py` (matplotlib + `plot_style.py`) or `.ps1` fallback -- **dev-plot** palette/linewidths. pgfplots only if `compat=1.14`. **Do not** leave "plot data on disk but not in PDF."

**Tables + figures:** every results subsection that has plots must also have a **metrics table** (Hand|Sim|error and/or corner/MC stats) immediately before or after the figures -- not figures alone.

#### Table completeness (mandatory)

**Lesson from prior runs:** agents often derive Hand numbers in `align` blocks but ship T4/T6/T7 with blank Hand cells or `no hand model` for core metrics. **That is a skill fail.** Algebra without mirrored table rows does not count as complete.

**Required tables (amplifiers)** -- create each when the corresponding stage ran; every data cell filled; **T1--T5 are mandatory on the primary PDK** (not "prefer"):

| Table ID | Where | Minimum columns (all cells filled) |
|----------|-------|--------------------------------------|
| T0 | Circuit under test | Device sizing: Role, Device, \(L\), \(W\), \(M\) (or mult) for **all** signal/bias FETs cited in §2; passives row or list |
| T1 | §2 Step 1 | Bias: Device / hand \(I_D\) / OP \(I_D\) / note (key branches + stage-2/3/FF) |
| T2 | §2 Step 2 | \(g_m\): Device / hand \(g_m\) (square-law or \(2I_D/V_{\mathrm{ov}}\)) / OP \(g_m\) -- **one row per** \(g_{m1},g_{m2},\ldots\) |
| T3 | §2 Step 3 | Stage / \(R_{\mathrm{out}}\) / \(A_{v}\) lin / \(A_{v}\) dB (all stages + overall \(A_0\)) |
| T4 | §2 Step 5 | Pole/zero: symbol / formula / Hand Hz / Sim Hz or `n/a (hand TF)` |
| T5 | §2 Step 7.1 + 7.5 | Branch map **and** power Hand\|Sim\|error\|Match? |
| T6 | Each healthy backend | Nominal: Metric / Hand / Sim / Rel. error / Match? -- **core rows** \(A_0\), GBW, PM, \(P\) **must have Hand numbers** (primary §2 or OP-\(g_m\) scale); extended rows may use `no hand model` |
| T7 | Each open PDK with §4c | Corners: corner / \(A_0\) / GBW / PM / power (+ vos if measured); mark FAIL/no-UGF |
| T8 | Each PDK with §4d | MC summary: mean/std or min/median/max for GBW and PM (and N, seed, mode); or one-row `HARD-SKIP: …` |
| T9 | Multi-backend | Cross-backend: Backend / \(A_0\) / GBW / PM / \(P\) (HARD-SKIP token if needed) |
| T10 | Match assessment | Gate table: Metric / Hand / Sim / Tol / Pass? for primary PDK |

**Empty-cell policy:** Forbidden in data cells: blank, `---`, `--`, `TBD`, `TODO`, `?`, `\ldots` used as a stand-in for a missing number. Allowed instead:

- Numeric value (with units in header or siunitx)
- `n/a` -- only when the column does not apply (e.g. Match? with no hand model; \(R_{\mathrm{out}}\) for overall \(A_0\) product row)
- `no hand model` -- Hand column **only** for CMRR/PSRR/noise/offset (etc.) when not derived -- **never** for core \(A_0\)/GBW/PM/\(P\) if §2 TF or OP-\(g_m\) scaling exists
- `HARD-SKIP: <reason>` -- backend/corner/MC unavailable
- `see §…` -- only as a **pointer beside** a still-filled number, never instead of the number

**Pre-PDF audit (step 6b):** Before claiming done:

1. Search `report.tex` for bare `---` / `& &` / `TBD` / `TODO` in `tabular` environments and fix them.
2. Confirm T0--T10 that apply exist; **confirm T1--T5 each contain Hand (or hand-equivalent) numeric columns**, not equations-only.
3. Confirm Step 4 has visible **4.0--4.4** and **4.3 has per-node KCL / Miller equations** (not only an \(A(s)\) equation).
4. Confirm every distinct \(g_m\) role has a numeric hand evaluation in Step 2 / T2.
5. Confirm T6 Hand for core rows is filled on every healthy backend (scale from primary if needed).

**Netlist appendix (required):** include the DUT `.subckt` (results copy) and fitted `.param` file via `\lstinputlisting` (package `listings`). Note upstream **path** / seed vars without suite branding.

## Definition of done

All must be true:

1. `report.pdf` with **TOC links**, full §2 algebra (anti-skip pass) including **Steps 4.0--4.4 with per-node 4.3 equations** and **7.1--7.5**, Step 8 when data allow; hand numbers from **final** OP; **mandatory T1--T5 Hand tables** mirrored from algebra; **metrics tables paired with figures**; **DUT netlist + params in appendix**.
2. `cmos` done (unless `pdk_only`) **and** every **default/requested** open PDK present (`sky130`/`ihp`/`gf180`) has nominal + corners + MC + §4e (or documented hard-skip/opt-out).
3. Comparison tables + cross-backend summary **fully filled** (T6--T10); no blank/`---` placeholder cells -- use typed `no hand model` / `HARD-SKIP: …` / `n/a` per §6.
4. **Figure checklist F1--F10** embedded or hard-skipped with reason; **F1/F2 include hand-vs-sim Bode overlays** per healthy backend when §2 TF exists.
5. Pre-PDF audit 6b passed (tables + TF depth).
6. **Single** `results/<run_id>/` remains for this DUT (no leftover timestamped siblings; paths in PDF/summary point only there).
7. User reply (English): PDF path, pass/fail per PDK, coverage, top mismatches, recovery notes.

**Not done:** headings without algebra; **equations without mandatory T1--T5 Hand tables**; **TF formula dump without how/why / without per-node 4.3 equations**; figures without tables (or vice versa for core metrics); **half-empty tables**; **`no hand model` on core \(A_0\)/GBW/PM/\(P\)** when a TF exists; missing netlist appendix; **dataset/suite branding** in report or user summary (AnalogGym or any other platform -- see Inputs); **non-English prose** (Chinese or other) in `report.tex` / PDF / `summary.md` / chat wrap-up; claiming CMRR/PSRR/noise/corners/MC without plots (or hard-skip); `cmos`-only evidence as PDK proof; skipping present IHP/GF180 without user opt-out or fetch failure note; TOC missing; **sim-only Bode when hand poles/zeros were derived** (must overlay or hard-skip with reason); **multiple timestamped / duplicate `results/` folders for the same analysis** (must consolidate to one main `results/<run_id>/`).

## Output to the user

1. Path to `report.pdf`
2. Pass/fail vs gates (per PDK)
3. Backends / corners / MC / extended specs (+ hard-skips)
4. Top 1--3 mismatches
5. §4b / fit changes if any

All of the above must be in **English** (see Language rule).

## Rules

- **Language (hard rule) -- English only.** Every user-visible spice-analyzer artifact and reply must be English: `report.tex` / `report.pdf` (title, TOC, sections, captions, tables, body, appendix notes), `summary.md`, `fit.md` / `recovery.md` / `mc_summary.md`, figure labels/titles drawn by plot scripts, and the final chat summary. Do **not** write Chinese (or other non-English prose) into reports or skill status messages -- including when a subagent authors LaTeX. Technical symbols, SI units, netlist identifiers, and verbatim source paths are fine. Before `pdflatex`, scan `report.tex` / `summary.md` for CJK (`[\u4e00-\u9fff]`) and remove/replace any hits. Prefer an explicit English `\date{...}` (or `english` babel) over locale-dependent `\today` on Chinese TeX installs (e.g. CTeX). **Plot titles/labels must be ASCII-only** (use `-` / `--`, never Unicode em-dash `—` or minus `−`): Windows PowerShell + System.Drawing often mojibakes those into CJK (e.g. `corners — UGF` -> `corners 欽?UGF`).
- **No dataset/platform branding** (AnalogGym or any other suite) -- path/paste only; analyze netlist contents (Inputs hard rule). Applies to PDF, `summary.md`, and chat.
- Prefer adapting a user-supplied TB when present; always copy adapted decks into `results/` only. Never require an in-repo benchmark TB.
- Never claim match without both hand and sim numbers.
- **No skipped intermediate algebra** (§2 anti-skip); **TF must include how/why (Steps 4.0--4.4) with per-node 4.3 equations**.
- **Power 7.1--7.5 mandatory.**
- **Tables fully filled** (T0--T10; **T1--T5 mandatory** with Hand columns mirrored from algebra; §6 empty-cell policy).
- **Do not** put Hand-only-in-equations; every Hand number needed later must appear in T1--T6 as applicable.
- **Embed plots** (checklist F1--F10); data files alone are insufficient.
- **F1/F2 hand TF overlay** on every healthy backend when §2 defines poles/zeros (see checklist).
- **Default to all present open PDKs** after `cmos`.
- Never treat stock/seed sizing failure as the end -- §3b / §4b.
- Do not commit `results/` unless asked; do not edit upstream source trees or PDK trees unless asked.
- Plot scripts live under **skill** `.agents/skills/spice-analyzer/plotting/` (not `tools/plotting/`).
- **One** `results/<run_id>/` per analysis (no leftover timestamped sibling folders; merge-then-delete if needed -- §3).

## Additional resources

- Plot recipes, TOC/hyperref skeleton, multi-PDK includes, corners/MC, hand-analysis depth (**TF how/why**), table templates, **source-path wording**: [reference.md](reference.md)
