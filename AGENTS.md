# Agent instructions (spice-analyzer)

This file is the shared source of truth for coding agents (Codex, Cursor, Claude Code, and others).

## Project purpose

Analyze analog SPICE netlists: small-signal hand analysis, ngspice simulation, theory-vs-sim comparison, and LaTeX/PDF reports under `results/`.

## Layout

| Path | Role |
|------|------|
| `.agents/skills/spice-analyzer/` | Canonical skill (`SKILL.md`, `reference.md`, **`plotting/`** tools) |
| `.agents/skills/spice-analyzer/plotting/` | Cross-platform figure renderers + Bode hand-TF overlay (Python + PowerShell) |
| `.cursor/skills/spice-analyzer` | Symlink → `.agents/skills/spice-analyzer` |
| `.claude/skills/spice-analyzer` | Symlink → `.agents/skills/spice-analyzer` |
| `.codex/skills/spice-analyzer` | Symlink → `.agents/skills/spice-analyzer` |
| `tools/` | Optional local samples / benches (any layout). **Not** part of the analyzer contract—netlists may come from anywhere |
| `models/pdk/` | Local PDK models (when present) |
| `results/` | Simulation decks, logs, figures, reports — **one** `results/<run_id>/` per analysis (no leftover timestamped siblings) |

Edit skills only under `.agents/skills/`. Do not duplicate skill bodies into tool-specific folders. If a tool path is a real copy instead of a symlink, fix it to point at `.agents/skills/spice-analyzer`. Plotting scripts must stay under the skill `plotting/` folder (not `tools/plotting/`).

## Tooling

- Simulator: **ngspice** (batch mode); on Windows, WSL or a portable/conda `ngspice_con` is fine if system packages are missing
- Reports: LaTeX → PDF (`latexmk` or `pdflatex`)
- Testbench: use a **user-supplied** TB when given; otherwise build a minimal ACDC bench from the DUT pins (do not require any in-repo benchmark suite)
- Open PDKs under `models/pdk/`: **sky130**, **ihp** (SG13G2), **gf180** — fetch via `models/pdk/fetch.sh` if needed

## Working rules

- Netlists are **source-agnostic**; never brand AnalogGym or any other dataset/platform in reports or chat (path/paste citation only—see skill Inputs). Treat any upstream tree as read-only unless asked to edit it; copy adapted decks into **one** `results/<run_id>/` (per-PDK `tb/` when multi-PDK). Prefer a stable DUT-derived run id; if intermediate/timestamped folders exist, merge needed artifacts into the main folder then delete the extras (skill §3)
- Do not claim theory/sim match without both hand analysis and measured sim numbers
- Do not commit `results/` artifacts unless the user asks
- Current skill focus: **amplifiers**; voltage references and other blocks are phased later (see the skill)
- **Do not stop early** on collapsed OP, placeholder/seed sizing (`W=L=1`), missing UGF, or a first FAIL table — enter skill §4b recovery and finish the loop (see skill Definition of done)
- Multi-PDK / corners / MC: follow skill §3b–§4d; **defaults are educational `cmos.lib` first, then every open PDK present (`sky130`, `ihp`, `gf180`); corners `tt,ff,ss`; MC N=200 mismatch; CMRR/PSRR/noise + embedded plots F1–F10; clickable TOC** unless the user opts out; amplifier reports must include **full hand algebra (anti-skip), TF Steps 4.0–4.4 with per-node 4.3 KCL/Miller equations (not formula dump), power Steps 7.1–7.5**, **mandatory Hand tables T1–T5 mirrored from the algebra** (equations-only is a fail), and **fully filled T6–T10** (no bare `---` / blank cells — use `no hand model` only for underived extended specs; never for core \(A_0\)/GBW/PM/\(P\) when a TF exists)

## Match gates (amplifier defaults)

Unless the user overrides:

- DC gain: within **±1 dB**
- GBW: within **±5%**
- Phase margin: within **±5°**
- Bias / power: within **±5%** when estimated

## When analyzing a netlist

Follow `.agents/skills/spice-analyzer/SKILL.md` (invoke as skill `spice-analyzer`).
