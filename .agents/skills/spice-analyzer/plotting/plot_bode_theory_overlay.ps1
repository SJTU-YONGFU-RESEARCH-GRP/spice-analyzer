# Plot Bode magnitude/phase: simulation vs hand-analysis TF overlay.
# Dev-plot palette: sim=#0033cc, hand=#cc0000
#
# Hand TF (amplifier default):
#   A(s) = A0 (1+s/wz) / [(1+s/wp1)(1+s/wp2)(1+s/wp3)]
# with RAFFC/NMC-style poles from OP gm and caps:
#   GBW = gm1/(2*pi*C0);  fp1 = GBW/A0;  fp2 = gm2/(2*pi*CL)*(C0/C1);
#   fp3 = gm3/(2*pi*C1);  fz = gmf/(2*pi*C0)
# Phase includes +180 deg when TB drives the inverting input (VINN).
#
# Usage (keep in sync with plot_bode_theory_overlay.py; both live in this skill plotting/ folder):
#   python3 .agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.py results/<run_id>
#   powershell -File .agents/skills/spice-analyzer/plotting/plot_bode_theory_overlay.ps1 -RunDir results/<run_id>
# Prefer the .py script on Unix and whenever matplotlib is available.

param(
  [Parameter(Mandatory = $true)][string]$RunDir,
  [string]$Backend = ""
)

Add-Type -AssemblyName System.Drawing

$C_BLUE = [System.Drawing.ColorTranslator]::FromHtml("#0033cc")
$C_RED  = [System.Drawing.ColorTranslator]::FromHtml("#cc0000")
$C_AXIS = [System.Drawing.Color]::FromArgb(40, 40, 40)
$C_GRID = [System.Drawing.Color]::FromArgb(90, 0, 0, 0)
$W = 900; $H = 560; $ML = 70; $MR = 24; $MT = 40; $MB = 58
$LW_MAIN = [single]2.2
$LW_SEC = [single]1.8
$FONT_T = [single]10
$FONT_L = [single]9
$FONT_A = [single]8

function Read-Params([string]$path) {
  $h = @{}
  if (-not (Test-Path $path)) { return $h }
  Get-Content $path | ForEach-Object {
    $line = $_.Trim()
    if ($line -match '^\s*#' -or $line -eq "") { return }
    if ($line -match '^([^=]+)=(.*)$') {
      $h[$matches[1].Trim()] = $matches[2].Trim()
    }
  }
  return $h
}

function Read-Xy([string]$path) {
  $pts = New-Object System.Collections.Generic.List[object]
  if (-not (Test-Path $path)) { return $pts }
  Get-Content $path | ForEach-Object {
    $p = $_.Trim() -split '\s+'
    if ($p.Count -ge 2) {
      try {
        $ff = [double]$p[0]; $yy = [double]$p[1]
        if ($ff -gt 0) { [void]$pts.Add([pscustomobject]@{ f = $ff; y = $yy }) }
      } catch {}
    }
  }
  return $pts
}

function Get-TheoryPoint([double]$f, [double]$A0, [double]$fp1, [double]$fp2, [double]$fp3, [double]$fz, [bool]$vinnDrive) {
  function MagFact([double]$fx) { return [math]::Sqrt(1.0 + ($f / $fx) * ($f / $fx)) }
  function ArgDeg([double]$fx) { return [math]::Atan($f / $fx) * 180.0 / [math]::PI }
  $magLin = $A0 * (MagFact $fz) / ((MagFact $fp1) * (MagFact $fp2) * (MagFact $fp3))
  $magDb = 20.0 * [math]::Log10([math]::Max($magLin, 1e-30))
  $ph = (ArgDeg $fz) - (ArgDeg $fp1) - (ArgDeg $fp2) - (ArgDeg $fp3)
  if ($vinnDrive) { $ph = 180.0 + $ph }
  return @{ mag = $magDb; ph = $ph }
}

function Plot-Overlay([string]$simDat, [string]$thyDat, [string]$outBase, [string]$title, [string]$ylab) {
  $sim = @(Read-Xy $simDat); $thy = @(Read-Xy $thyDat)
  if ($sim.Count -lt 2 -or $thy.Count -lt 2) { Write-Host "skip overlay $outBase"; return }
  $bmp = New-Object System.Drawing.Bitmap $W, $H
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.SmoothingMode = "AntiAlias"
  $g.Clear([System.Drawing.Color]::White)
  $pw = $W - $ML - $MR; $ph = $H - $MT - $MB
  $penSpine = New-Object System.Drawing.Pen $C_AXIS, 1.2
  $g.DrawRectangle($penSpine, $ML, $MT, $pw, $ph)
  $penGrid = New-Object System.Drawing.Pen $C_GRID, 0.8
  for ($i = 1; $i -le 4; $i++) {
    $yy = $MT + $ph * $i / 5.0
    $g.DrawLine($penGrid, $ML, $yy, ($ML + $pw), $yy)
  }
  $fontT = New-Object System.Drawing.Font "Arial", $FONT_T, ([System.Drawing.FontStyle]::Bold)
  $fontL = New-Object System.Drawing.Font "Arial", $FONT_L, ([System.Drawing.FontStyle]::Bold)
  $fontA = New-Object System.Drawing.Font "Arial", $FONT_A, ([System.Drawing.FontStyle]::Bold)
  $sz = $g.MeasureString($title, $fontT)
  $g.DrawString($title, $fontT, [System.Drawing.Brushes]::Black, (($W - $sz.Width) / 2), 10)
  $szx = $g.MeasureString("Frequency (Hz)", $fontL)
  $g.DrawString("Frequency (Hz)", $fontL, [System.Drawing.Brushes]::Black, (($W - $szx.Width) / 2), ($H - 32))
  $g.TranslateTransform(14, ($H / 2)); $g.RotateTransform(-90)
  $szy = $g.MeasureString($ylab, $fontL)
  $g.DrawString($ylab, $fontL, [System.Drawing.Brushes]::Black, (-$szy.Width / 2), 0)
  $g.ResetTransform()

  $all = @($sim) + @($thy)
  $fmin = ($all | Measure-Object f -Minimum).Minimum
  $fmax = ($all | Measure-Object f -Maximum).Maximum
  $ymin = ($all | Measure-Object y -Minimum).Minimum
  $ymax = ($all | Measure-Object y -Maximum).Maximum
  if ($ymax -eq $ymin) { $ymax = $ymin + 1 }
  $logspan = [math]::Log10($fmax / $fmin)

  function DrawSeries($pts, $color, $lw) {
    $pen = New-Object System.Drawing.Pen $color, ([single]$lw)
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $first = $true; $prev = $null
    foreach ($pt in $pts) {
      $x = $ML + $pw * [math]::Log10($pt.f / $fmin) / $logspan
      $y = $MT + $ph * (1 - ($pt.y - $ymin) / ($ymax - $ymin))
      $cur = [System.Drawing.PointF]::new($x, $y)
      if ($first) { $path.StartFigure(); $first = $false } else { $path.AddLine($prev, $cur) }
      $prev = $cur
    }
    $g.DrawPath($pen, $path); $pen.Dispose()
  }
  DrawSeries $sim $C_BLUE $LW_MAIN
  DrawSeries $thy $C_RED $LW_SEC
  $g.FillRectangle((New-Object System.Drawing.SolidBrush $C_BLUE), ($ML + 8), ($MT + 8), 28, 9)
  $g.DrawString("Sim", $fontA, [System.Drawing.Brushes]::Black, ($ML + 42), ($MT + 2))
  $g.FillRectangle((New-Object System.Drawing.SolidBrush $C_RED), ($ML + 8), ($MT + 26), 28, 9)
  $g.DrawString("Hand TF", $fontA, [System.Drawing.Brushes]::Black, ($ML + 42), ($MT + 20))
  $g.DrawString(("{0:G4}" -f $ymax), $fontA, [System.Drawing.Brushes]::Black, 4, ($MT - 2))
  $g.DrawString(("{0:G4}" -f $ymin), $fontA, [System.Drawing.Brushes]::Black, 4, ($MT + $ph - 12))
  $bmp.Save("$outBase.png", [System.Drawing.Imaging.ImageFormat]::Png)
  Write-Host "wrote $outBase.png"
  $g.Dispose(); $bmp.Dispose()
}

function Process-Backend([string]$run, [string]$be) {
  $fig = Join-Path $run "$be\figures"
  $simDir = Join-Path $run "$be\sim"
  $paramPath = Join-Path $simDir "hand_tf_params.txt"
  if (-not (Test-Path (Join-Path $fig "bode_mag.dat"))) {
    Write-Host "skip ${be}: missing bode_mag.dat"; return
  }
  $p = Read-Params $paramPath
  if (-not $p.ContainsKey("A0_lin") -or -not $p.ContainsKey("fp1_Hz")) {
    Write-Host "skip ${be}: missing hand_tf_params.txt (need A0_lin, fp1_Hz, ...)"; return
  }
  $A0 = [double]$p["A0_lin"]
  $fp1 = [double]$p["fp1_Hz"]
  $fp2 = [double]$p["fp2_Hz"]
  $fp3 = [double]$p["fp3_Hz"]
  $fz = [double]$p["fz_Hz"]
  $vinn = $true
  if ($p.ContainsKey("vinn_drive") -and $p["vinn_drive"] -eq "0") { $vinn = $false }

  $simMag = Join-Path $fig "bode_mag.dat"
  $freqs = New-Object System.Collections.Generic.List[double]
  Get-Content $simMag | ForEach-Object {
    $parts = $_.Trim() -split '\s+'
    if ($parts.Count -ge 2) {
      try { [void]$freqs.Add([double]$parts[0]) } catch {}
    }
  }
  if ($freqs.Count -lt 10) {
    $f = 1.0
    while ($f -le 1e9 + 1) { [void]$freqs.Add($f); $f *= 1.059253725 }
  }

  $magLines = New-Object System.Collections.Generic.List[string]
  $phLines = New-Object System.Collections.Generic.List[string]
  foreach ($f in $freqs) {
    if ($f -le 0) { continue }
    $t = Get-TheoryPoint $f $A0 $fp1 $fp2 $fp3 $fz $vinn
    [void]$magLines.Add(("{0:E10}  {1:E10}" -f $f, $t.mag))
    [void]$phLines.Add(("{0:E10}  {1:E10}" -f $f, $t.ph))
  }
  $magLines | Set-Content -Encoding ascii (Join-Path $fig "bode_mag_theory.dat")
  $phLines | Set-Content -Encoding ascii (Join-Path $fig "bode_phase_theory.dat")

  Plot-Overlay (Join-Path $fig "bode_mag.dat") (Join-Path $fig "bode_mag_theory.dat") `
    (Join-Path $fig "bode_mag_overlay") "$be Bode magnitude: sim vs hand" "Gain (dB)"
  Plot-Overlay (Join-Path $fig "bode_phase.dat") (Join-Path $fig "bode_phase_theory.dat") `
    (Join-Path $fig "bode_phase_overlay") "$be Bode phase: sim vs hand" "Phase (deg)"
}

$backends = @()
if ($Backend) { $backends = @($Backend) }
else {
  foreach ($cand in @("cmos", "sky130", "ihp", "gf180")) {
    if (Test-Path (Join-Path $RunDir "$cand\figures\bode_mag.dat")) { $backends += $cand }
  }
}

foreach ($be in $backends) { Process-Backend $RunDir $be }
Write-Host "done backends: $($backends -join ', ')"
