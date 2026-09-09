# spice-analyzer plotting (lives inside the skill — Unix + Windows)

Vendored **dev-plot** style for amplifier report figures. This folder is part of
`.agents/skills/spice-analyzer/` so the skill stays self-contained when the rest
of the repo is cleared.

| File | Role | Platform |
|------|------|----------|
| `plot_style.py` | Canonical constants (column-embed fonts/lines) | both |
| `render_spice_figures.py` | Preferred figure renderer → PNG + SVG | both (needs matplotlib) |
| `render_spice_figures.ps1` | Windows fallback (System.Drawing) → PNG | Windows |
| `plot_bode_theory_overlay.py` | Sim vs hand TF Bode overlay (F1/F2) | both (needs matplotlib) |
| `plot_bode_theory_overlay.ps1` | Same overlay, System.Drawing | Windows |
| `render_all.sh` | One-shot: render + Bode overlay | Unix / macOS / WSL |
| `render_all.ps1` | One-shot: Python if available else `.ps1` | Windows |

**Style contract:** report figures use `FIGSIZE_COL*` with `TITLE_SIZE=10`, `LABEL_SIZE=9`,
`TICK_SIZE=8`, `LINEWIDTH_MAIN=2.2`. Dashboard aliases (`*_DASHBOARD`) are not for PDFs.
Keep `.ps1` bitmap size (~900×560 @ 200 dpi) and fonts in sync with `plot_style.py`.


Paths below are relative to the **skill root** (or use the symlink
`.cursor/skills/spice-analyzer/plotting/` / `.claude/...` / `.codex/...`).

## Preferred (any OS with Python + matplotlib)

```bash
# from repo root, or any cwd — pass absolute or relative run dir
SKILL=./.agents/skills/spice-analyzer   # or .cursor/skills/spice-analyzer
python3 "$SKILL/plotting/render_spice_figures.py" results/<run_id>
python3 "$SKILL/plotting/plot_bode_theory_overlay.py" results/<run_id>
bash "$SKILL/plotting/render_all.sh" results/<run_id>
```

## Windows without matplotlib

```powershell
$SKILL = ".agents\skills\spice-analyzer"   # or .cursor\skills\spice-analyzer
powershell -File "$SKILL\plotting\render_all.ps1" -RunDir results/<run_id>
```

Hand TF overlay expects `<run_id>/<backend>/sim/hand_tf_params.txt` (see skill `reference.md`).
