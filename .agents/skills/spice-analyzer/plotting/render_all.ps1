# One-shot: render spice-analyzer figures + Bode hand-TF overlay (Windows).
# Prefer Python+matplotlib; else System.Drawing .ps1 siblings in this folder.
param(
  [Parameter(Mandatory = $true)][string]$RunDir
)

$ErrorActionPreference = "Stop"
$PlotDir = $PSScriptRoot
$RunDir = (Resolve-Path $RunDir).Path

$py = $null
foreach ($cand in @("python", "python3", "py")) {
  $cmd = Get-Command $cand -ErrorAction SilentlyContinue
  if ($cmd) { $py = $cand; break }
}

$usePy = $false
if ($py) {
  & $py -c "import matplotlib" 2>$null
  if ($LASTEXITCODE -eq 0) { $usePy = $true }
}

if ($usePy) {
  Write-Host "== render_spice_figures.py =="
  & $py (Join-Path $PlotDir "render_spice_figures.py") $RunDir
  Write-Host "== plot_bode_theory_overlay.py =="
  & $py (Join-Path $PlotDir "plot_bode_theory_overlay.py") $RunDir
} else {
  Write-Host "== render_spice_figures.ps1 (no matplotlib) =="
  & powershell -NoProfile -File (Join-Path $PlotDir "render_spice_figures.ps1") -RunDir $RunDir
  Write-Host "== plot_bode_theory_overlay.ps1 =="
  & powershell -NoProfile -File (Join-Path $PlotDir "plot_bode_theory_overlay.ps1") -RunDir $RunDir
}

Write-Host "done: $RunDir"
