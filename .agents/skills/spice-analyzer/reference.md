# Spice Analyzer Reference

## Amplifier pin convention (AnalogGym)

Subcircuit pin order used by `TB_Amplifier_ACDC.cir`:

```
Xop gnda vdda vinn vinp vout <subckt_name>
```

Unity-gain AC loop in the TB uses large L/C feedback (`Lfb`, `Cin`) between `opout` and `signal_in`.

## Amplifier metrics (phase 1)

From ACDC TB `.meas` / control:

| Key | Meaning |
|-----|---------|
| `dcgain` | Differential DC gain (dB) at low freq |
| `gain_bandwidth_product` / GBP | Unity-gain frequency |
| `phase_in_deg` | Phase at unity gain (PM related) |
| `cmrrdc` | Common-mode gain proxy for CMRR setup |
| `DCPSRp` / `DCPSRn` | Supply rejection setups |
| `power` | DC power at 25 °C |
| `vos25` | Offset-related measure in unity-gain DC TB |
| `tc` | Output tempco over DC temp sweep |

Transient TB (`TB_Amplifier_Tran.cir`) adds slew / settling; use when user asks transient validation.

`perf_extraction_amp.py` lists: `cmrrdc`, `dcgain`, `gbp`, `phase_in_rad`, `phase_in_deg`, `dcpsrp`, `dcpsrn`, `tc`, `power`, `vos25`, `t_rise`, `t_fall`, `area`, …

## Voltage reference metrics (phase 2 stub)

Typical targets when enabled:

- \(V_{\mathrm{ref}}\) at nominal T / VDD
- TC (ppm/°C) over stated range
- Line sensitivity / LSR
- Quiescent current / power

See `tools/AnalogGym/AnalogGym/Voltage Reference/` descriptions for stimulus patterns.

## LaTeX report skeleton

Save as `results/<run_id>/report.tex`:

```latex
\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,booktabs,graphicx,hyperref,siunitx}
\title{Spice Analyzer Report: \<CIRCUIT\>}
\author{spice-analyzer}
\date{\today}
\begin{document}
\maketitle

\section{Circuit under test}
% Netlist path, topology, PDK/corner, bias, load

\section{Small-signal analysis}
% Hand derivations, assumptions, predicted metrics

\section{Simulation setup}
% TB path, ngspice version, analyses run (AC/DC/tran)

\section{Results}
\begin{table}[h]
\centering
\begin{tabular}{@{}lrrr@{}}
\toprule
Metric & Hand & Sim & Rel.\ error \\
\midrule
DC gain (dB) &  &  &  \\
GBW &  &  &  \\
Phase margin (deg) &  &  &  \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[h]
\centering
% \includegraphics[width=0.85\linewidth]{figures/bode_mag.pdf}
\caption{AC response}
\end{figure}

\section{Match assessment}
% Pass/fail vs gates; mismatch discussion

\section{Appendix}
% Key netlist excerpts, meas log snippets
\end{document}
```

## Run layout

```
results/
  <run_id>/
    report.tex
    report.pdf
    tb/           # copied/adapted decks + netlist snapshot
    sim/          # ngspice log, raw print/meas
    figures/      # bode, etc.
    summary.md
```

## Tooling notes

- Simulator: `ngspice` (batch `-b`)
- PDF: `latexmk -pdf` or `pdflatex`
- On this Windows host, run tools via `wsl` when native binaries are missing
