#!/usr/bin/env bash
# One-shot: render spice-analyzer figures + Bode hand-TF overlay (Unix/macOS/WSL).
# Lives next to the other plotting scripts inside the skill.
set -euo pipefail
PLOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUN_DIR="${1:?Usage: $0 <run_dir>  e.g. results/<run_id> or absolute path}"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "error: python3/python not found" >&2
  exit 1
fi

# Resolve run dir to absolute for stable writes
if [[ "$RUN_DIR" != /* ]]; then
  RUN_DIR="$(pwd)/$RUN_DIR"
fi

echo "== render_spice_figures =="
"$PY" "$PLOT_DIR/render_spice_figures.py" "$RUN_DIR"

echo "== plot_bode_theory_overlay =="
"$PY" "$PLOT_DIR/plot_bode_theory_overlay.py" "$RUN_DIR"

echo "done: $RUN_DIR"
