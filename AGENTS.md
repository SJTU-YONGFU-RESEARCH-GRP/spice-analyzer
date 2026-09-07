# Agent instructions (spice-analyzer)

This file is the shared source of truth for coding agents (Codex, Cursor, Claude Code, and others).

## Project purpose

Analyze analog SPICE netlists: small-signal hand analysis, ngspice simulation, theory-vs-sim comparison, and LaTeX/PDF reports under `results/`.

## Layout

| Path | Role |
|------|------|
| `.agents/skills/spice-analyzer/` | Canonical skill (`SKILL.md`, `reference.md`) |
| `.cursor/skills/spice-analyzer` | Symlink → `.agents/skills/spice-analyzer` |
| `.claude/skills/spice-analyzer` | Symlink → `.agents/skills/spice-analyzer` |
| `.codex/skills/spice-analyzer` | Symlink → `.agents/skills/spice-analyzer` |
| `tools/AnalogGym/` | Git submodule — benchmark circuits / TBs |
| `models/pdk/` | Local PDK models (when present) |
| `results/` | Simulation decks, logs, figures, reports |

Edit skills only under `.agents/skills/`. Do not duplicate skill bodies into tool-specific folders.

## Tooling

- Simulator: **ngspice** (batch mode)
- Reports: LaTeX → PDF (`latexmk` or `pdflatex`)
- On Windows, prefer **WSL** if native `git` / `ngspice` / LaTeX are missing
- AnalogGym amp TB: `tools/AnalogGym/AnalogGym/Amplifier/amp_spice_testbench/TB_Amplifier_ACDC.cir`

## Working rules

- Treat AnalogGym as read-only unless the user asks to change upstream files; copy adapted decks into `results/<run_id>/tb/`
- Do not claim theory/sim match without both hand analysis and measured sim numbers
- Do not commit `results/` artifacts unless the user asks
- Current skill focus: **amplifiers**; voltage references and other blocks are phased later (see the skill)

## When analyzing a netlist

Follow `.agents/skills/spice-analyzer/SKILL.md` (invoke as skill `spice-analyzer`).
