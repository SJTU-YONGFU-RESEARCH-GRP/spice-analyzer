# spice-analyzer

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-green?logo=creativecommons&logoColor=white)](https://creativecommons.org/licenses/by/4.0/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776ab.svg)](https://www.python.org/downloads/)

Analyze analog SPICE netlists with step-by-step small-signal hand analysis, multi-PDK **ngspice** simulation (corners and Monte Carlo), theory-vs-sim comparison, and LaTeX/PDF reports under `results/`. The workflow is an agent skill (`spice-analyzer`) shared across Codex, Cursor, and Claude Code.

- **License**: CC BY 4.0 (see [`LICENSE`](LICENSE))
- **Canonical skill**: [`.agents/skills/spice-analyzer`](.agents/skills/spice-analyzer)
- **Agent instructions**: [`AGENTS.md`](AGENTS.md)

## Table of contents

- [Features](#features)
- [Requirements](#requirements)
- [Agent setup](#agent-setup)
- [Quick start](#quick-start)
  - [1. Fetch open PDK models](#1-fetch-open-pdk-models)
  - [2. Run an analysis (agents)](#2-run-an-analysis-agents)
  - [3. Render report figures](#3-render-report-figures)
- [Match gates](#match-gates)
- [Project layout](#project-layout)
- [License](#license)
- [References](#references)

## Features

| Area | What you get |
|------|----------------|
| Hand analysis | Full small-signal algebra for amplifiers (bias, \(g_m\), stage gains, TF Steps 4.0–4.4, GBW/PM, power) with mandatory Hand tables T1–T5 |
| Simulation | Educational `cmos.lib` first, then every open PDK present under `models/pdk/` (sky130, IHP SG13G2, GF180) |
| Corners / MC | Default corners `tt,ff,ss`; Monte Carlo N=200 mismatch (unless opted out) |
| Specs & plots | CMRR, PSRR, noise, corner/MC bars, hand-vs-sim Bode overlays (F1–F10) |
| Reports | Clickable-TOC LaTeX → PDF under one `results/<run_id>/` |
| Scope | Phase 1: amplifiers (op-amp / OTA). Voltage references and other blocks are planned later |

Netlists are **source-agnostic**: paste, local path, or any folder. Do not brand upstream suites or datasets in reports (path/paste citation only). See the skill [Inputs](.agents/skills/spice-analyzer/SKILL.md) section.

## Requirements

- A coding agent that can load skills (Cursor / Claude Code / Codex), or follow [`.agents/skills/spice-analyzer/SKILL.md`](.agents/skills/spice-analyzer/SKILL.md) manually
- **ngspice** (batch mode). On Windows: WSL or portable/conda `ngspice_con` (IHP needs ngspice **≥41** + OSDI)
- **LaTeX** (`latexmk` or `pdflatex`) for PDF reports
- **Python 3.10+** with `matplotlib` and `numpy` for preferred figure rendering (PowerShell `.ps1` fallbacks exist on Windows without matplotlib)
- Optional open PDK trees via [`models/pdk/fetch.sh`](models/pdk/fetch.sh) (Git Bash / WSL)

## Agent setup

| File | Purpose |
|------|---------|
| [`AGENTS.md`](AGENTS.md) | Shared agent instructions (Codex, Cursor, …) |
| [`CLAUDE.md`](CLAUDE.md) | Claude Code adapter → imports `AGENTS.md` |
| [`.agents/skills/spice-analyzer`](.agents/skills/spice-analyzer) | Canonical skill (`SKILL.md`, `reference.md`, `plotting/`) |

Symlinks under `.cursor/skills`, `.claude/skills`, and `.codex/skills` point at the same skill directory. Edit skills only under `.agents/skills/`; do not duplicate skill bodies into tool-specific folders.

## Quick start

### 1. Fetch open PDK models

Educational Level-1 cards live in [`models/cmos.lib`](models/cmos.lib) (see [`models/README.md`](models/README.md)). Open foundry primitives are optional and fetched into `models/pdk/`:

```bash
cd models/pdk
./fetch.sh --all
# or: ./fetch.sh --sky130 --ihp --gf180
```

### 2. Run an analysis (agents)

Provide a netlist (path or paste) and ask the agent to use skill **`spice-analyzer`**. Defaults (unless you opt out):

1. Educational `cmos` smoke, then every present open PDK
2. Corners `tt,ff,ss` on PDKs
3. Monte Carlo N=200 mismatch
4. Full amp specs, embedded plots, and a PDF under `results/<run_id>/`

Useful overrides (see skill): `sky130_only`, `cmos_only`, `no_corners`, `no_mc`, user-supplied testbench, expected specs.

Artifacts for one analysis stay in a **single** `results/<run_id>/` folder (per-PDK `tb/` when multi-PDK). Do not commit `results/` unless asked.

### 3. Render report figures

After sim data exists under `results/<run_id>/`:

```bash
SKILL=./.agents/skills/spice-analyzer
python3 "$SKILL/plotting/render_spice_figures.py" results/<run_id>
python3 "$SKILL/plotting/plot_bode_theory_overlay.py" results/<run_id>
bash "$SKILL/plotting/render_all.sh" results/<run_id>
```

Windows (Python preferred; else System.Drawing fallbacks):

```powershell
$SKILL = ".agents\skills\spice-analyzer"
powershell -File "$SKILL\plotting\render_all.ps1" -RunDir results\<run_id>
```

Details: [`.agents/skills/spice-analyzer/plotting/README.md`](.agents/skills/spice-analyzer/plotting/README.md).

## Match gates

Unless overridden for a run:

| Metric | Tolerance |
|--------|-----------|
| DC gain | ±1 dB |
| GBW | ±5% |
| Phase margin | ±5° |
| Bias / power (when estimated) | ±5% |

Do not claim theory/sim match without both hand analysis and measured sim numbers.

## Project layout

```text
.
├── AGENTS.md                          # Shared agent rules
├── CLAUDE.md                          # Claude adapter → AGENTS.md
├── LICENSE
├── README.md
├── .agents/skills/spice-analyzer/     # Canonical skill
│   ├── SKILL.md                       # Workflow, tables, definition of done
│   ├── reference.md                   # Metrics, plots, PDK notes
│   └── plotting/                      # Bode overlay + figure renderers
├── .cursor/skills/spice-analyzer      # Symlink → .agents/...
├── .claude/skills/spice-analyzer      # Symlink → .agents/...
├── .codex/skills/spice-analyzer       # Symlink → .agents/...
├── models/
│   ├── cmos.lib / cap.lib / opamp.lib # Educational models
│   ├── README.md
│   └── pdk/
│       ├── fetch.sh                   # sky130 / ihp / gf180
│       └── wrappers/                  # Local SPICE wrappers
├── tools/                             # Optional local samples (gitignored)
└── results/<run_id>/                  # Per-run decks, logs, figures, PDF
```

Plotting scripts must stay under the skill `plotting/` folder (not `tools/plotting/`).

## License

This project is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See [`LICENSE`](LICENSE).

**Third-party assets** (open PDK trees under `models/pdk/`, vendor model licenses) remain under their respective licenses; see the `LICENSE` files inside each fetched PDK directory.

## References

- Skill workflow: [`.agents/skills/spice-analyzer/SKILL.md`](.agents/skills/spice-analyzer/SKILL.md)
- Metrics and plot IDs: [`.agents/skills/spice-analyzer/reference.md`](.agents/skills/spice-analyzer/reference.md)
- Educational models: [`models/README.md`](models/README.md)
- Figure tooling: [`.agents/skills/spice-analyzer/plotting/README.md`](.agents/skills/spice-analyzer/plotting/README.md)
- ngspice: https://ngspice.sourceforge.io/
