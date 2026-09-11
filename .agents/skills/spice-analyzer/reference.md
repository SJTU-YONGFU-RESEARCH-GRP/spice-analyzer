# Spice Analyzer Reference

## Source path / no suite branding

Reports and chat must stay **source-agnostic**:

| Do | Don't |
|----|--------|
| `Source path: \texttt{path/to/file}` or "user-provided paste" | "AnalogGym amp," "\<Suite\> check," "from the AmpGym corpus" |
| Circuit/subckt name, pin list, topology | Suite name in `\section` / `\caption` / TOC |
| "Original design variables (seeds)" | "Original \<Suite\> design variables" |

This applies to **every** hosting tree (`tools/AnalogGym/`, future `tools/<anything>/`, external foundry folders, class repos). Path strings may contain those folder names; **prose must not elevate them to product branding.**

## Language -- English only

Hard rule (see skill Rules): **all report and skill-facing prose is English.**

| Do | Don't |
|----|--------|
| English section titles, captions, tables, `summary.md`, chat wrap-up | Chinese (or other non-English) sentences in TeX/PDF/Markdown/chat |
| `\date{8 September 2026}` or `\usepackage[english]{babel}` + safe `\today` | Relying on CTeX / Chinese Windows locale for `\today` (may print 年月日) |
| ASCII-heavy TeX; math via `amsmath` / `siunitx` | Pasting CJK into `\caption`, `\section`, or plot titles |
| Plot titles with ASCII `-` / `--` only | Unicode em-dash `—` / minus `−` in `.ps1` titles (mojibakes to CJK on Windows) |
| Pre-PDF grep for `[\u4e00-\u9fff]` in `report.tex` / `summary.md` | Shipping a PDF after a Chinese-language subagent draft without scrubbing |

Plot script string literals (matplotlib / System.Drawing titles and axis labels) must also stay English.

## Agentic model provenance (table TA)

Every report must record **which AI host/product and model(s)** ran the spice-analyzer workflow. This is independent of SPICE/PDK device models.

**Artifacts:**

| Path | Content |
|------|---------|
| `report.tex` → PDF | `\section{Analysis provenance}` + **table TA** (TOC entry) |
| `results/<run_id>/agent_provenance.md` | Same facts in Markdown (English) |
| `summary.md` | Short "Agentic models:" bullet mirroring TA |

**Do / Don't:**

| Do | Don't |
|----|--------|
| Host product (Cursor, Claude Code, Codex, \ldots) + model display name | Leave TA blank or omit the section |
| Slug/id when known (`claude-opus-4-6`, `gpt-5.4`, \ldots) | Invent a model name the host did not disclose |
| One row per distinct model / subagent role | Confuse TA with BSIM / `cmos.lib` / PDK rows |
| `unknown (not disclosed by host)` in Model if needed | Soft-delete provenance because the slug is hidden |
| Skill path `.agents/skills/spice-analyzer` under the table | Brand dataset suites in Notes |

**LaTeX skeleton (TA):**

```latex
\section{Analysis provenance}
\subsection{Agentic models}
% Table TA -- fill every cell; add a row per distinct model / subagent.
\begin{center}
{\small
\begin{tabular}{@{}llllp{0.28\linewidth}@{}}
\toprule
Role & Host & Model & Scope & Notes \\
\midrule
Primary orchestrator & Cursor & Composer & ingest--report & skill spice-analyzer \\
% Hand-analysis author & ... & ... & §2 & ... \\
% Simulation / recovery & ... & ... & §3--4e & ... \\
% Report LaTeX & ... & ... & §6 & ... \\
\bottomrule
\end{tabular}}
\end{center}
\footnotesize Skill path: \texttt{.agents/skills/spice-analyzer}.
Optional: ngspice version, OS, plot backend (Python / PowerShell).
```

**`agent_provenance.md` template:**

```markdown
# Agentic provenance

- Skill: spice-analyzer (`.agents/skills/spice-analyzer`)
- Run id: <run_id>
- Date: <ISO or English date>

| Role | Host | Model | Scope | Notes |
|------|------|-------|-------|-------|
| Primary orchestrator | Cursor | Composer | ingest--report | single-agent run |

Toolchain (optional): ngspice <ver>; plots via Python|PowerShell.
```

---

## Amplifier pin convention

Document the DUT subcircuit pin order from the netlist (do not assume a fixed order). Example patterns:

```
Xop gnda vdda vinn vinp vout <subckt_name>
```

or other supply/input/output orders -- **match the `.subckt` line**.

Unity-gain AC loops (when used) typically isolate DC feedback with large \(L\)/\(C\) so AC sees the open-loop path while DC bias closes. If the TB drives the **inverting** input, LF phase ~180 deg; report PM with the same convention as the TB (`phase_at_UGF` in degrees) -- state the convention explicitly in Step 6.

## Amplifier metrics (phase 1)

**Default (measure on every healthy backend):**

| Key | Meaning |
|-----|---------|
| `dcgain` | Differential DC gain (dB) at low freq |
| `gain_bandwidth_product` / GBP / UGF | Unity-gain frequency |
| `phase_in_deg` / PM | Phase at unity gain -> phase margin |
| `cmrrdc` / `CMRR(f)` | Common-mode rejection (DC + AC sweep) |
| `DCPSRp` / `DCPSRn` / `PSRR(f)` | Positive / negative supply rejection |
| `noise` / `en_1k` / `en_1M` | Input-referred noise density; spots @ 1 kHz & 1 MHz |
| `power` | DC power at stated temperature |
| `vos25` | Unity-gain offset proxy |
| `tc` | Output tempco when TB has temp sweep |

**Preferred:** transient slew / settle / \(\mathrm{FOM}_L\).

**Match gates (unless overridden):** DC gain +/-1 dB; GBW +/-5%; PM +/-5 deg; bias/power +/-5% when estimated.

### Mandatory plots (amplifiers) -- must appear in PDF

| ID | Figure | Source | Export |
|----|--------|--------|--------|
| F1 | Bode magnitude (**sim + hand TF**) | ACDC + §2 | `bode_mag.dat` + `bode_mag_theory.dat` -> `bode_mag_overlay.png` |
| F2 | Bode phase (**sim + hand TF**) | ACDC + §2 | `bode_phase.dat` + `bode_phase_theory.dat` -> `bode_phase_overlay.png` |
| F3 | CMRR vs \(f\) | ACM | `figures/cmrr.dat` |
| F4--F5 | PSRR+ / PSRR- vs \(f\) | PSRR TB | overlay `figures/psrr.png` (or separate) |
| F6 | \(e_n(f)\) density | `.noise` | `figures/noise.dat` + annotate 1 kHz / 1 MHz |
| F7 | Corner bars | §4c | `figures/corners.csv` |
| F8 | MC hist -- GBW | §4d | `mc_*_hist.csv` |
| F9 | MC hist -- PM | §4d | |
| F10 | Cross-backend bars | >=2 backends | `figures_cross.csv` |

### Hand TF vs simulation Bode overlay (F1/F2) -- required

For each healthy backend, after §2 and nominal ACDC:

1. Write `<backend>/sim/hand_tf_params.txt` from **final OP** \(g_m\) and compensation caps (example RAFFC/NMC-style keys):

```text
A0_lin=<linear DC gain from hand or 10^(Adc_dB/20)>
gm1_S=... gm2_S=... gm3_S=... gmf_S=...
C0_F=... C1_F=... CL_F=...
GBW_Hz=gm1/(2*pi*C0)
fp1_Hz=GBW/A0_lin
fp2_Hz=gm2/(2*pi*CL)*(C0/C1)   # topology-specific -- match §2
fp3_Hz=gm3/(2*pi*C1)
fz_Hz=gmf/(2*pi*C0)
vinn_drive=1   # 1 if TB AC-drives VINN (add +180 deg to theory phase)
```

2. Generate theory curves + overlay PNGs (dev-plot: **blue=sim**, **red=hand**). Prefer Python on Unix and Windows; PowerShell is the Windows fallback. All scripts live under the skill `plotting/` folder (not `tools/plotting/`):

```bash
# Unix / macOS / WSL / any OS with Python+matplotlib (preferred)
python3 .agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.py results/<run_id>
python3 .agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.py results/<run_id> --backend sky130
bash .agents/skills/spice-analyzer/plotting/render_all.sh results/<run_id>

# Windows PowerShell fallback (no matplotlib)
powershell -File .agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.ps1 -RunDir results/<run_id>
powershell -File .agents/skills/spice-analyzer/plotting/render_all.ps1 -RunDir results/<run_id>
```

3. Embed `bode_mag_overlay.png` / `bode_phase_overlay.png` in the PDF for F1/F2 (not sim-only plots). Keep raw `.dat` files for audit.

4. Hard-skip overlay only with a one-line PDF reason (e.g. no pole/zero model yet); still ship sim Bode.

Also run the usual figure renderer for F3--F10:

```bash
# Preferred (cross-platform)
python3 .agents/skills/spice-analyzer/plotting/render_spice_figures.py results/<run_id>

# Windows fallback
powershell -File .agents/skills/spice-analyzer/plotting/render_spice_figures.ps1 -RunDir results/<run_id>
```

### Plot rendering (dev-plot style) -- required

Canonical style: skill `plotting/plot_style.py` (Cursor **dev-plot** skill). Ship **both** Python and PowerShell entry points so agents can run on Linux CI or Windows laptops.

| Token | Value (column embed) |
|-------|-------|
| Primary / secondary / accent | `#0033cc` / `#cc0000` / `#7f3fbf` |
| Linewidth main / secondary | `2.2` / `1.8` (not dashboard 7/5) |
| Bar fill / edge | `#0033cc` / `#002080` |
| Spines | all visible, width `1.2` |
| Title / label / tick / legend | `10` / `9` / `8` / `8` bold sans |
| LaTeX column embed | figsize `(4.5, 2.8)` / wide `(4.5, 3.0)` in @ 200 dpi |
| Bode overlay | sim = primary blue; hand TF = secondary red |

**Typography rule:** sizes in `plot_style.py` are for **column embeds**. Do not apply dashboard sizes (`TITLE_SIZE_DASHBOARD=17`, `LINEWIDTH_MAIN_DASHBOARD=7`) to report figures -- that overflows titles and makes font weight look inconsistent across Bode / bar / hist panels.

| Script | Unix | Windows |
|--------|------|---------|
| All figures + Bode overlay | `bash .agents/skills/spice-analyzer/plotting/render_all.sh results/<run_id>` | `powershell -File .agents/skills/spice-analyzer/plotting/render_all.ps1 -RunDir results/<run_id>` |
| Figures only | `python3 .agents/skills/spice-analyzer/plotting/render_spice_figures.py ...` | same, or `.ps1` fallback |
| Bode overlay only | `python3 .agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.py ...` | same, or `.ps1` fallback |

```bash
python3 .agents/skills/spice-analyzer/plotting/render_spice_figures.py results/<run_id>
python3 .agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.py results/<run_id>
bash .agents/skills/spice-analyzer/plotting/render_all.sh results/<run_id>
powershell -File .agents/skills/spice-analyzer/plotting/render_all.ps1 -RunDir results/<run_id>
powershell -File .agents/skills/spice-analyzer/plotting/render_spice_figures.ps1 -RunDir results/<run_id>
powershell -File .agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.ps1 -RunDir results/<run_id>
```

**Rules:**

- Embed PNG via `\includegraphics`; keep SVG when matplotlib ran.
- Do not use ad-hoc colors, `tab10`, or thin lines.
- Do not use `\pgfplotsset{compat=1.17}` on old MiKTeX (empty axes). Prefer pre-rendered PNG.
- After `pdflatex`, open the PDF and confirm curves/bars are visible.
- Hard-skip a plot only with a one-line PDF + `summary.md` reason.
- Noise: after `.noise`, `setplot noise1` then `wrdata ... inoise_spectrum`.
- **Do not** leave F1/F2 as sim-only when `hand_tf_params.txt` could be written from §2.
- Prefer **Python** scripts on Unix; on Windows use Python when available, otherwise `.ps1` fallbacks. Keep both pairs in sync (palette + **column** fontsize/linewidth from `plot_style.py`).
- Re-run `render_all` after changing `plot_style.py` so all backends share one look.

---

## Hand-analysis depth (anti-skip examples)

**Recurring failure mode:** agents write correct-looking `align` algebra but ship the PDF with missing T1--T5, Hand-empty metrics tables, or Step 4.3 that jumps from "RAFFC" to a 3p1z formula. Treat **tables + per-node TF equations** as first-class deliverables, not optional polish.

### Step 1 -- bias table (T1) is mandatory

After the \(I_k=M_k/M_{\mathrm{ref}}\cdot I_b\) lines, include:

```latex
\begin{center}
\begin{tabular}{lrrl}
\toprule
Device & Hand $I_D$ & OP $I_D$ & Note \\
\midrule
M0 & ... & ... & $I_b$ \\
... & ... & ... & ... \\
\bottomrule
\end{tabular}
\end{center}
```

Every branch that carries significant current in OP (including stage-2/3/FF) needs a row. Label OP-assisted hand explicitly when mirror ratios are compressed.

### Step 2 -- show both square-law and OP (when possible) -- every \(g_m\) role

```text
gm_hand = sqrt(2 * KP * (W/L)*M * ID)
        = sqrt(2 * 100e-6 * (20/0.5)*8 * 20e-6) = ... S
gm_op   = <from .op>  (use this in Steps 3--8)
```

Repeat **full arithmetic** for each distinct role (\(g_{m1},g_{m2},g_{m3},g_{mf}\)). One worked example plus "similarly for the others" **fails**. Then **mandatory \(g_m\) table (T2)** with Hand and OP columns.

### Step 3 -- numeric \(R_{\mathrm{out}}\) trail + T3

```text
gds_drv = <OP>            ->  ro_drv  = 1/gds_drv = ...
gds_load = <OP>           ->  ro_load = 1/gds_load = ...
Rout1   = ro_drv || ro_load       [= value with both operands shown]
Av1     = gm1 * Rout1             [= value]
A0      = Av1*Av2*Av3             [= value, dB]
```

Cascode: expand \(g_m r_{o,\mathrm{cas}} r_{o,\mathrm{bot}}\) with **substituted numbers** before paralleling with the load side. If only OP `gds` is trustworthy on a PDK, say so and compute \(r_o=1/g_{ds}\) from sim -- do not skip the arithmetic. **Do not** replace the stage trail with only "use measured \(A_0\)" on the primary PDK. Ship **T3** (stage / \(R_{\mathrm{out}}\) / \(A_v\) lin / dB).

### Step 4 -- transfer function how/why (mandatory 4.0--4.4)

Agents often fail by pasting a reduced \(A(s)\) and pole formulas with no derivation. Require the following structure in the PDF.

#### 4.0 Signal path (prose template)

```text
Topology: <Miller | NMC | RAFFC | ...>
Stage 1: devices <...> at node <net_x> -> v1
Stage 2: devices <...> at node <net_y> -> v2
Stage 3 / output: devices <...> at VOUT
Feedforward (if any): <Mgmf> from <node> to VOUT
Caps: C0 between <net_a>--<net_b>; C1 between <...>; CL at VOUT
```

#### 4.1 Small-signal model (what is kept)

List retained \(g_m\), lump \(R_i\) (or \(r_o\) parallels), and caps. Explicitly list neglected \(C_{gs}/C_{gd}\) if the hand GBW is meant to match the first 1--2 decades of the sim Bode only.

#### 4.2--4.3 Worked sketches (copy the matching topology; adapt node names)

**Minimum for 4.3:** write KCL at each retained node, then list approximations as separate lines, then the reduced \(A(s)\). Do not jump from topology name to the final rational function.

**Two-stage Miller (classic):**

Node equations (example pattern -- adapt names):

\[
\begin{aligned}
v_1&: \quad g_{m1}v_{\mathrm{id}} + \frac{v_1}{R_1} + s C_c(v_1-v_{\mathrm{out}})=0,\\
v_{\mathrm{out}}&: \quad g_{m2}v_1 + \frac{v_{\mathrm{out}}}{R_2} + s C_L v_{\mathrm{out}} + s C_c(v_{\mathrm{out}}-v_1)=0.
\end{aligned}
\]

Approximations (state explicitly): \(A_2=g_{m2}R_2\gg 1\); dominant pole from Miller \(C_c(1+A_2)\); neglect \(s^2\) below GBW.

Why poles/zeros:

- Dominant \(\omega_{p1}\): Miller-multiplied \(C_c\) at the high-resistance stage-1 node \(\Rightarrow \omega_{p1}\approx 1/(R_1 A_2 C_c)\).
- GBW / unity-gain rate: \(\omega_t\approx g_{m1}/C_c\) (integrator asymptote after the dominant pole).
- Output ND pole \(\omega_{p2}\approx g_{m2}/C_L\) (or \(g_{m2} C_c/(C_1 C_L)\) form if splitting \(C_c\) loading -- state which).
- RHP zero \(\omega_z\approx g_{m2}/C_c\): feedforward through \(C_c\) opposes the \(g_{m2}\) path.

Reduced TF (after stating Miller approx):

\[
A(s)\approx A_0\frac{1-s/\omega_z}{(1+s/\omega_{p1})(1+s/\omega_{p2})},\quad
A_0=g_{m1}R_1\cdot g_{m2}R_2.
\]

**Three-stage NMC / RNMC (inner + outer nested Miller):**

Write KCL at the inner and outer compensated nodes before quoting poles. Why:

- Outer loop sets \(\omega_t\sim g_{m1}/C_c\) (or topology-specific \(C_0\)).
- Inner compensation cap sets a higher pole involving \(g_{m2}\) and the inner node cap.
- State whether the inner loop is assumed ideal (buffered) or not; if RNMC, note the series resistance and its LHP/RHP zero role.

**RAFFC / AFFC-style (active feedback + feedforward):**

Nodes (map to netlist names in 4.0): \(v_1\) (e.g. first high-Z), \(v_2\) (inner), \(v_{\mathrm{out}}\); caps \(C_0\), \(C_1\), \(C_L\); FF \(g_{mf}\).

Example KCL skeleton (adapt signs/attachments to the actual schematic):

\[
\begin{aligned}
v_1&: \quad g_{m1}v_{\mathrm{id}}+\frac{v_1}{R_1}+s C_1(v_1-v_2)+\cdots=0,\\
v_2&: \quad g_{m2}v_1+\frac{v_2}{R_2}+s C_1(v_2-v_1)+\cdots=0,\\
v_{\mathrm{out}}&: \quad g_{m3}v_2+g_{mf}v_1+\frac{v_{\mathrm{out}}}{R_3}+s C_L v_{\mathrm{out}}+s C_0(\cdots)=0.
\end{aligned}
\]

Then state approximations **line by line**, e.g.:

1. \(A_{v2}A_{v3}\gg 1\) \(\Rightarrow\) outer loop integrates with \(\omega_t\approx g_{m1}/C_0\).
2. Neglect device \(C_{gs}/C_{gd}\) vs \(C_0,C_1,C_L\) near GBW.
3. Drop \(s^2\) cross terms below GBW \(\Rightarrow\) factor into 3p1z.

Why (typical reduced 3p1z used with \(C_0,C_1,C_L\)):

- \(\omega_t=g_{m1}/C_0\): input stage charges the main compensation / feedback cap that closes the outer loop.
- \(\omega_{p1}=\omega_t/A_0\): dominant pole implied by DC gain and GBW (integrator form).
- \(\omega_{p2}\propto (g_{m2}/C_L)(C_0/C_1)\): stage-2 drives the load while the cap ratio accounts for the nested / splitting compensation network -- **write the one-line reason for the \(C_0/C_1\) factor from your nodal approx** (do not leave it unexplained).
- \(\omega_{p3}\propto g_{m3}/C_1\): stage-3 (or inner) node against the smaller cap.
- LHP \(\omega_z\propto g_{mf}/C_0\): feedforward \(g_{mf}\) injects a zero that partially cancels ND-pole lag.

Then write:

\[
A(s)=A_0\frac{1+s/\omega_z}{(1+s/\omega_{p1})(1+s/\omega_{p2})(1+s/\omega_{p3})}
\]

with each \(\omega\) given symbolically (Step 4.4) before numeric Step 5. Citing a paper alone does **not** replace the KCL / approximation trail.

#### 4.4 Named formulas before numbers

```text
omega_t  = gm1 / C0
omega_p1 = omega_t / A0
omega_p2 = (gm2 / CL) * (C0 / C1)    # must match 4.2 reason
omega_p3 = gm3 / C1
omega_z  = gmf / C0
```

### Step 4--6 -- name then substitute + T4 / PM table

For each of \(\omega_{p1},\omega_{p2},\omega_z\): **symbol definition -> formula -> number**.
**T4 columns:** symbol / formula / Hand Hz / Sim Hz (or `n/a (hand TF)`).
For PM: print each \(\tan^{-1}(\omega_t/\omega_{p,k})\) **argument and** degrees, then sum -- prefer a PM term table (Hand vs Sim).

### Step 7.2 -- include large branches + T5

Bias-only \(\sum I\) is incomplete when stage-2/3/FF dominate \(I_{DD}\). Either:

- express stage-3 from mirror \(M\) relative to a known diode current, or
- take stage-3 from OP and label "OP-assisted hand," then still sum explicitly.

**Power Steps 7.1--7.5 are mandatory** (branch-map **table**, ideal currents, hand power, sim OP, **Hand|Sim|error|Match?** compare table vs +/-5%).

---

## Table completeness (templates)

Bare `---` in Hand/error/Match columns is a **skill fail**. Use typed placeholders only as below.

**Hard rule:** if a Hand number appears in §2 equations, it **must** also appear in T1--T5 / T6. `no hand model` is **only** for underived extended specs (CMRR/PSRR/noise/...), never for core \(A_0\)/GBW/PM/\(P\) when a TF or OP-\(g_m\) scaling exists.

### Agentic provenance (TA) -- every run

See [Agentic model provenance](#agentic-model-provenance-table-ta) above. Ship TA in the PDF **and** `agent_provenance.md` before claiming done.

### §2 tables (T1--T5) -- primary PDK

Copy these skeletons into `report.tex` (fill every cell):

**T1 bias**

```latex
\begin{tabular}{lrrl}
\toprule Device & Hand $I_D$ & OP $I_D$ & Note \\
\midrule ... & ... & ... & ... \\
\bottomrule
\end{tabular}
```

**T2 \(g_m\)**

```latex
\begin{tabular}{lrrl}
\toprule Device/role & Hand $g_m$ & OP $g_m$ & Used later \\
\midrule ... & ... & ... & OP \\
\bottomrule
\end{tabular}
```

**T3 stage gain**

```latex
\begin{tabular}{lrrr}
\toprule Stage & $R_{\mathrm{out}}$ & $A_v$ (lin) & $A_v$ (dB) \\
\midrule 1 & ... & ... & ... \\
Overall $A_0$ & n/a (product) & ... & ... \\
\bottomrule
\end{tabular}
```

**T4 poles/zeros**

```latex
\begin{tabular}{llrr}
\toprule Symbol & Formula & Hand (Hz) & Sim (Hz) \\
\midrule GBW & $g_{m1}/(2\pi C_0)$ & ... & ... \\
\bottomrule
\end{tabular}
```

**T5 branch map + power compare** -- device paths table, then Hand|Sim|error|Match? for \(I_{DD}\)/\(P\).

### Nominal metrics (T6) -- healthy backend

```latex
\begin{center}
\begin{tabular}{lrrrl}
\toprule
Metric & Hand & Sim & Rel.\ error & Match? \\
\midrule
\(A_0\) (dB) & 110.3 & 110.3 & 0\,dB & PASS \\
UGF (MHz) & 3.92 & 4.41 & \(+12.6\%\) & FAIL \\
PM (deg) & 106.3 & 82.3 & \(\Delta 24^\circ\) & FAIL \\
\(P\) (mW) & 0.532 & 0.532 & \(0\%\) & PASS \\
CMRR (dB) & no hand model & \(-70.8\) & n/a & n/a \\
PSRR+ (dB) & no hand model & \(-66.7\) & n/a & n/a \\
PSRR- (dB) & no hand model & \(-75.5\) & n/a & n/a \\
\(e_n\) 1\,kHz & no hand model & 581\,nV/\(\sqrt{\mathrm{Hz}}\) & n/a & n/a \\
\(e_n\) 1\,MHz & no hand model & 46.9\,nV/\(\sqrt{\mathrm{Hz}}\) & n/a & n/a \\
\bottomrule
\end{tabular}
\end{center}
```

If PM hand was not fully re-derived on a secondary PDK, **scale** Step 6 with that PDK's OP \(g_m\) (or same ND ratios as primary) and still fill a Hand number -- do **not** write `no hand model` for PM/GBW/\(A_0\)/\(P\) when a TF model exists, and do not leave `---` while Sim is filled.

**Match? column:** whenever Hand and Sim are both numeric for a core metric, Match? must be `PASS` or `FAIL` against the default gates. Use `n/a` in Match? **only** when Hand is `no hand model`. Keep Hand cells short so Match? is not clipped; put long notes under the table.

**BSIM / PDK realism:** hand analysis is a reduced model. Close match on every gate vs foundry BSIM is hard -- **FAIL is an acceptable honest outcome**. Prefer documenting the mismatch (e.g. PM lag from parasitics) over hiding Match? or claiming PASS without numbers. Official sign-off remains the **primary PDK** T10 table; other backends still show PASS/FAIL for transparency.

### Corner table (T7)

Include **power** (and vos if measured). Every corner row filled; use `no-UGF` / `FAIL` in a status column when needed.

### MC table (T8) or hard-skip row

```latex
% Either statistics:
% N, mode, seed | GBW mean/std | PM mean/std
% Or:
HARD-SKIP: <one-line reason>
```

### Cross-backend (T9)

```latex
ihp & HARD-SKIP: OSDI unavailable on this host &
  HARD-SKIP & HARD-SKIP & HARD-SKIP \\
```

Do not use four bare `---` cells plus a note only in prose.

### Pre-PDF grep hints

```bash
# Flag common empty-cell patterns in tables (agent must fix hits):
rg -n '\\\\begin\{tabular\}|&\\s*---\\s*&|&\\s*&|TBD|TODO' results/<run_id>/report.tex
```

Also confirm headings `Step 4` / `4.0` / `4.1` / signal-path / "why" prose exist -- not only an `A(s)=` equation.

---
## Educational CMOS (`models/cmos.lib`)

Token: `cmos`. Include: `models/cmos.lib`.

- Map foundry FETs -> `nmos_rvt` / `pmos_rvt` unless hvt/nat/tox/dep required.
- Teaching rail ~1.8 V; MC via `.param mc=1` LOT.
- Always label **educational** in the PDF.

## Voltage reference metrics (phase 2 stub)

\(V_{\mathrm{ref}}\), TC, line sensitivity, quiescent current -- same algebra depth when enabled.

---

## Multi-PDK (sky130 / IHP / GF180)

**Agent default:** after `cmos`, run **every tree that exists**:

| Token | Directory | Typical \(V_{DD}\) | Notes |
|-------|-----------|-------------------|--------|
| `sky130` | `models/pdk/sky130_fd_pr/` | 1.8 V | `scale=1.0u`; X-instance `m=` |
| `gf180` | `models/pdk/gf180mcu_fd_pr/` | 3.3 V | `.lib sm141064.ngspice <corner>` |
| `ihp` | `models/pdk/ihp-sg13g2/` | 1.2 V LV | ngspice >=41 + OSDI; `.spiceinit` loads `osdi/*.osdi` |

Fetch: `cd models/pdk && ./fetch.sh --all` (or `--sky130|--gf180|--ihp`).

Missing tree -> hard-skip that token with fetch hint; do **not** silently omit without a PDF note.

### Fitting vs smoke

| Mode | Intent |
|------|--------|
| **Smoke** | Same um \(W/L\) across PDKs; label smoke |
| **Fit** | Retarget per process for healthy OP + gates / journal tables |

### Model include cheatsheet

**Sky130 (minimal FET):**

```spice
.option scale=1.0u
.param mc_mm_switch=0
.param mc_pr_switch=0
.include '.../models/parameters/lod.spice'
.include '.../cells/nfet_01v8/sky130_fd_pr__nfet_01v8__mismatch.corner.spice'
.include '.../cells/pfet_01v8/sky130_fd_pr__pfet_01v8__mismatch.corner.spice'
.include '.../cells/nfet_01v8/sky130_fd_pr__nfet_01v8__tt.pm3.spice'
.include '.../cells/pfet_01v8/sky130_fd_pr__pfet_01v8__tt.pm3.spice'
```

Corners: swap `tt` -> `ff` / `ss` in the pm3 filenames (keep `mismatch.corner.spice`).

**Sky130 MC:** override `*_vth0_slope_spectre`, `*_toxe_slope_spectre`, `*_voff_slope_spectre` with `agauss(0,1,1)` after includes; `setseed` + `reset` per trial. Save scalars to CSV (avoid `print` of whole AC vectors).

**GF180:**

```spice
.lib '.../models/ngspice/sm141064.ngspice' typical
```

Map to `nmos_3p3` / `pmos_3p3` (or 6 V if required). Corners: `typical|ff|ss|...`.

**IHP SG13G2:**

```spice
* work-dir .spiceinit must load osdi/psp103*.osdi
.lib '.../libs.tech/ngspice/models/cornerMOSlv.lib' mos_tt
```

Remap to `sg13_lv_nmos` / `sg13_lv_pmos` (confirm in lib). For process MC use **typical** + vendor mismatch/stat libs -- see PDK notes.

### Device remap checklist

1. Copy DUT -> `results/<run_id>/<pdk>/tb/`.
2. Replace model names; map `m` / `mult` / fingers.
3. Fix \(V_{DD}\), \(V_{CM}\).
4. Fit if OP collapses.
5. One-page `sim/fit.md`.

---

## Corners

| PDK | Default set |
|-----|-------------|
| sky130 | `tt`, `ff`, `ss` |
| gf180 | `typical`, `ff`, `ss` |
| ihp | `mos_tt`, `mos_ff`, `mos_ss` |

Table columns: corner, \(A_0\), GBW, PM, power, vos, pass/fail. **Also** figure F7.

---

## Monte Carlo (MC)

| PDK | Mechanism |
|-----|-----------|
| sky130 | slope_spectre + `agauss` / mismatch.corner |
| gf180 | stat/mismatch libs if present; else hard-skip |
| ihp | typical + mismatch/stat libs; else hard-skip |

Default N=200 mismatch. Deliverables: `mc_results.csv`, `mc_summary.md`, figures F8--F9.

---

## LaTeX report skeleton (TOC + tables + plots + netlist)

```latex
\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,booktabs,graphicx,siunitx,listings}
\usepackage[hidelinks]{hyperref}
\usepackage{bookmark}
\lstset{basicstyle=\ttfamily\scriptsize,breaklines=true,frame=single}
\title{Spice Analyzer Report: \<CIRCUIT\>}
\author{spice-analyzer}
% Prefer an explicit English date -- CTeX / zh locale can make \today print Chinese.
\date{\today} % or e.g. \date{8 September 2026}
\begin{document}
\maketitle
\tableofcontents
\clearpage
% Language: English only in all sections, captions, and tables (skill Rules).

\section{Analysis provenance}
\subsection{Agentic models}
% Table TA: Role | Host | Model | Scope | Notes (mandatory).
% Mirror to agent_provenance.md and a short bullet in summary.md.
% Do not invent model ids; use ``unknown (not disclosed by host)'' if needed.
\subsection{Toolchain notes}
% Optional: ngspice version, OS, Python vs PowerShell plots.

\section{Circuit under test}
\subsection{Netlist and topology}
% Source path: verbatim filesystem path OR ``user-provided paste'' only.
% NEVER name AnalogGym / AmpGym / other benchmark suites in titles or captions.
\subsection{Device sizing table}
\subsection{Backends, corners, MC scope}

\section{Small-signal analysis (step-by-step)}
% Steps 0--8 with intermediate tables (bias, gm, Av, poles, PM, power)
% Step 4 MUST include 4.0 signal path, 4.1 small-signal model,
% 4.2 why each pole/zero, 4.3 derive reduced A(s), 4.4 named formulas
% -- not only a final A(s) equation.

\section{Simulation setup}

\section{Results --- educational CMOS}
\subsection{Metrics table}  % Hand|Sim|error|Match -- no bare --- cells
\subsection{Figures}  % F1--F5 (+ F6 if available)

\section{Results --- sky130}
\subsection{Nominal metrics table}   % Hand | Sim | error | Match?
\subsection{Bode / CMRR / PSRR figures}
\subsection{Corners --- table and figures}  % include power column
\subsection{Monte Carlo --- table and figures}  % or HARD-SKIP row

\section{Results --- IHP SG13G2}
\section{Results --- GF180}

\section{Cross-backend comparison}
\subsection{Summary table}  % HARD-SKIP token in cells if needed
\subsection{Figures}  % F10

\section{Match assessment}
% gate table PASS/FAIL -- all cells filled

\section{Appendix}
\subsection{Notes}
\subsection{DUT netlist}
\lstinputlisting{<pdk>/tb/dut.spice}
\subsection{Fitted parameters}
\lstinputlisting{<pdk>/tb/params.spice}
\end{document}
```

**Required content rules:**

- **Agentic provenance:** table **TA** + `agent_provenance.md` (skill §6); TOC section before Circuit under test.
- **Table + figure:** each results block that embeds plots must also show a metrics / corner / MC **table** (not figures alone).
- **Filled cells:** every required table TA + T0--T10 applicable to the run; no blank/`---`/`TBD` data cells -- see Table completeness above and skill §6.
- **TF how/why:** Step 4 substeps 4.0--4.4 in the PDF.
- **Netlist appendix:** `\lstinputlisting` of the results-copy DUT + fitted params (primary PDK). Note upstream path and seeds.
- Prefer `\includegraphics{...png}` from skill `.agents/skills/spice-analyzer/plotting/` (dev-plot). Avoid fragile high `pgfplots` compat on old MiKTeX.

**TOC requirements:**

- Use numbered `\section` / `\subsection` (avoid `*` for TOC entries).
- `\usepackage{hyperref}` + `\tableofcontents` after `\maketitle`; compile **twice**.
- Optional `\usepackage{bookmark}`.
- Avoid raw math in subsection titles (breaks bookmarks); use plain text or `\texorpdfstring`.

**Figure snippet:**

```latex
\begin{figure}[ht]
\centering
\includegraphics[width=0.88\linewidth]{sky130/figures/bode_mag_overlay.png}
\caption{sky130 TT -- Bode magnitude sim+hand overlay (F1).}
\end{figure}
```

---

## Definition of done (short)

PDF with **clickable TOC** + **TA agentic provenance** + anti-skip Steps 0--7.5 (+8) including **TF Steps 4.0--4.4 (how/why)** + **fully filled tables TA + T0--T10** (no bare `---` cells) + `cmos` + **each present open PDK** (or hard-skip) + corners/MC + CMRR/PSRR/noise + **figures F1--F10** embedded or hard-skipped. No "data on disk only." F1/F2 must be hand-vs-sim overlays when §2 poles/zeros exist (blue=sim, red=hand) or hard-skipped with reason.

## Run layout

**One analysis = one folder.** Use a stable `results/<run_id>/` (DUT-derived name preferred). Do **not** keep parallel timestamped siblings (`*_YYYYMMDD*`) for the same DUT. If partial work landed elsewhere, merge unique files into the main folder, fix path citations, then delete the extras.

```
results/<run_id>/
  report.tex / report.pdf / summary.md / agent_provenance.md
  cmos/{tb,sim,figures}/
  sky130/{tb,sim,figures}/
  ihp/{tb,sim,figures}/
  gf180/{tb,sim,figures}/
```

## Tooling notes

- ngspice batch `-b`; IHP needs OSDI-capable >=41
- PDF: `latexmk -pdf` or `pdflatex` x2
- Windows: portable `tools/ngspice/.../ngspice_con.exe` is fine
- PDK fetch: `models/pdk/fetch.sh --all`
- Plots: skill `.agents/skills/spice-analyzer/plotting/` (not `tools/plotting/`)

## Recovery checklist (skill §4b)

| # | Check / action |
|---|----------------|
| 1 | Pin order; supplies; `Cload` |
| 2 | \(V_{CM}\) for input type |
| 3 | PDK includes (LOD/mismatch; GF `.lib`; IHP OSDI) |
| 4 | Multiplicity map |
| 5 | Fit placeholder \(W/L/M\) for **this** PDK |
| 6 | Re-run ACDC; healthy OP |
| 7 | Re-derive hand §2 + power 7.1--7.5 |
| 8 | Log `recovery.md` / `fit.md` |

## Healthy OP quick tests

- Mid-rail \(V_{\mathrm{out}}\); sensible \(V_{GS}/V_{SG}\); `dcgain` \(\ge 40\,\mathrm{dB}\) intent; UGF exists

## Corner / MC / plot checklist

| # | Action |
|---|--------|
| 1 | Nominal healthy before sweep |
| 2 | Corners simulated; FAIL marked; F7 in PDF |
| 3 | MC N/mode/seed recorded; F8--F9 in PDF |
| 4 | F1--F6 noise/CMRR/PSRR in PDF per healthy backend |
| 5 | F10 if multi-backend; hard-skips explained |
| 6 | F1/F2 overlays from `hand_tf_params.txt` when §2 TF exists |
