# Render spice-analyzer figures with Cursor dev-plot palette/geometry (no matplotlib).
# Colors/linewidths match sibling plot_style.py (skill plotting/)
param(
  [Parameter(Mandatory = $true)][string]$RunDir
)

Add-Type -AssemblyName System.Drawing

$C_BLUE = [System.Drawing.ColorTranslator]::FromHtml("#0033cc")
$C_RED = [System.Drawing.ColorTranslator]::FromHtml("#cc0000")
$C_PURPLE = [System.Drawing.ColorTranslator]::FromHtml("#7f3fbf")
$C_BAR_EDGE = [System.Drawing.ColorTranslator]::FromHtml("#002080")
$C_GRID = [System.Drawing.Color]::FromArgb([int](0.35 * 255), 0, 0, 0)
$C_AXIS = [System.Drawing.Color]::FromArgb(40, 40, 40)

# Column-embed @ 200dpi -- keep in sync with plot_style.py FIGSIZE_COL / typography
$W = 900
$H = 560
$ML = 70; $MR = 24; $MT = 40; $MB = 58
$LW_MAIN = [single]2.2
$LW_SEC = [single]1.8
$SPINE = [single]1.2
$FONT_T = [single]10
$FONT_L = [single]9
$FONT_A = [single]8

function New-Font([string]$name, [single]$size, [System.Drawing.FontStyle]$style) {
  return [System.Drawing.Font]::new($name, $size, $style, [System.Drawing.GraphicsUnit]::Point)
}

function Read-Xy([string]$path) {
  $pts = New-Object System.Collections.Generic.List[object]
  Get-Content $path | ForEach-Object {
    $p = $_.Trim() -split '\s+'
    if ($p.Count -ge 2) {
      try {
        $f = [double]$p[0]; $y = [double]$p[1]
        if ($f -gt 0) { [void]$pts.Add([pscustomobject]@{ f = $f; y = $y }) }
      } catch {}
    }
  }
  return $pts
}

function Save-Canvas([System.Drawing.Bitmap]$bmp, [string]$outBase) {
  $dir = Split-Path $outBase -Parent
  if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  $png = "$outBase.png"
  $bmp.Save($png, [System.Drawing.Imaging.ImageFormat]::Png)
  Write-Host "wrote $png"
}

function New-Canvas() {
  $bmp = New-Object System.Drawing.Bitmap $W, $H
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.SmoothingMode = "AntiAlias"
  $g.TextRenderingHint = "ClearTypeGridFit"
  $g.Clear([System.Drawing.Color]::White)
  return @{ bmp = $bmp; g = $g }
}

function Draw-Frame($g, [string]$title, [string]$xlabel, [string]$ylabel) {
  $pw = $W - $ML - $MR; $ph = $H - $MT - $MB
  $penSpine = New-Object System.Drawing.Pen $C_AXIS, $SPINE
  $g.DrawRectangle($penSpine, $ML, $MT, $pw, $ph)
  # grid
  $penGrid = New-Object System.Drawing.Pen $C_GRID, 1.1
  for ($i = 1; $i -le 4; $i++) {
    $yy = $MT + $ph * $i / 5.0
    $g.DrawLine($penGrid, $ML, $yy, ($ML + $pw), $yy)
  }
  $fontT = New-Font "Arial" $FONT_T ([System.Drawing.FontStyle]::Bold)
  $fontL = New-Font "Arial" $FONT_L ([System.Drawing.FontStyle]::Bold)
  $fontA = New-Font "Arial" $FONT_A ([System.Drawing.FontStyle]::Bold)
  $brush = [System.Drawing.Brushes]::Black
  $sz = $g.MeasureString($title, $fontT)
  $g.DrawString($title, $fontT, $brush, (($W - $sz.Width) / 2), 10)
  $szx = $g.MeasureString($xlabel, $fontL)
  $g.DrawString($xlabel, $fontL, $brush, (($W - $szx.Width) / 2), ($H - 32))
  # rotated ylabel
  $g.TranslateTransform(14, ($H / 2))
  $g.RotateTransform(-90)
  $szy = $g.MeasureString($ylabel, $fontL)
  $g.DrawString($ylabel, $fontL, $brush, (-$szy.Width / 2), 0)
  $g.ResetTransform()
  return @{ fontA = $fontA; pw = $pw; ph = $ph; penSpine = $penSpine; penGrid = $penGrid; fontT = $fontT; fontL = $fontL }
}

function Plot-LogLine([string]$dat, [string]$outBase, [string]$title, [string]$ylab, $color, [single]$lw = 2.2) {
  if (-not (Test-Path $dat)) { Write-Host "skip missing $dat"; return }
  $pts = Read-Xy $dat
  if ($pts.Count -lt 2) { Write-Host "skip empty $dat"; return }
  $c = New-Canvas
  $g = $c.g; $bmp = $c.bmp
  $fr = Draw-Frame $g $title "Frequency (Hz)" $ylab
  $fmin = $pts[0].f; $fmax = $pts[$pts.Count - 1].f
  $ymin = ($pts | Measure-Object y -Minimum).Minimum
  $ymax = ($pts | Measure-Object y -Maximum).Maximum
  if ($ymax -eq $ymin) { $ymax = $ymin + 1 }
  $logspan = [math]::Log10($fmax / $fmin)
  $pen = New-Object System.Drawing.Pen $color, $lw
  $path = New-Object System.Drawing.Drawing2D.GraphicsPath
  $first = $true
  foreach ($pt in $pts) {
    $x = $ML + $fr.pw * [math]::Log10($pt.f / $fmin) / $logspan
    $y = $MT + $fr.ph * (1 - ($pt.y - $ymin) / ($ymax - $ymin))
    if ($first) { $path.StartFigure(); $prev = [System.Drawing.PointF]::new($x, $y); $first = $false }
    else { $path.AddLine($prev, [System.Drawing.PointF]::new($x, $y)); $prev = [System.Drawing.PointF]::new($x, $y) }
  }
  $g.DrawPath($pen, $path)
  $g.DrawString(("{0:G4}" -f $ymax), $fr.fontA, [System.Drawing.Brushes]::Black, 4, ($MT - 2))
  $g.DrawString(("{0:G4}" -f $ymin), $fr.fontA, [System.Drawing.Brushes]::Black, 4, ($MT + $fr.ph - 12))
  $g.DrawString(("{0:G3}" -f $fmin), $fr.fontA, [System.Drawing.Brushes]::Black, $ML, ($MT + $fr.ph + 4))
  $g.DrawString(("{0:G3}" -f $fmax), $fr.fontA, [System.Drawing.Brushes]::Black, ($ML + $fr.pw - 70), ($MT + $fr.ph + 4))
  Save-Canvas $bmp $outBase
  $g.Dispose(); $bmp.Dispose(); $pen.Dispose()
}

function Plot-PsrrOverlay([string]$pPlus, [string]$pMinus, [string]$outBase, [string]$title) {
  if (-not ((Test-Path $pPlus) -and (Test-Path $pMinus))) { Write-Host "skip PSRR missing $pPlus / $pMinus"; return }
  $a = @(Read-Xy $pPlus); $b = @(Read-Xy $pMinus)
  if ($a.Count -lt 2 -or $b.Count -lt 2) { Write-Host "skip empty PSRR $outBase"; return }
  $c = New-Canvas; $g = $c.g; $bmp = $c.bmp
  $fr = Draw-Frame $g $title "Frequency (Hz)" "Gain (dB)"
  $all = @($a) + @($b)
  $fmin = ($all | Measure-Object f -Minimum).Minimum
  $fmax = ($all | Measure-Object f -Maximum).Maximum
  $ymin = ($all | Measure-Object y -Minimum).Minimum
  $ymax = ($all | Measure-Object y -Maximum).Maximum
  if ($ymax -eq $ymin) { $ymax = $ymin + 1 }
  $logspan = [math]::Log10($fmax / $fmin)
  function DrawSeries($pts, $color) {
    $pen = New-Object System.Drawing.Pen $color, $LW_SEC
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $first = $true
    foreach ($pt in $pts) {
      $x = $ML + $fr.pw * [math]::Log10($pt.f / $fmin) / $logspan
      $y = $MT + $fr.ph * (1 - ($pt.y - $ymin) / ($ymax - $ymin))
      if ($first) { $path.StartFigure(); $script:prev = [System.Drawing.PointF]::new($x, $y); $first = $false }
      else { $path.AddLine($script:prev, [System.Drawing.PointF]::new($x, $y)); $script:prev = [System.Drawing.PointF]::new($x, $y) }
    }
    $g.DrawPath($pen, $path); $pen.Dispose()
  }
  DrawSeries $a $C_BLUE
  DrawSeries $b $C_RED
  # legend
  $fontA = $fr.fontA
  $g.FillRectangle((New-Object System.Drawing.SolidBrush $C_BLUE), ($ML + 8), ($MT + 8), 18, 6)
  $g.DrawString("PSRR+", $fontA, [System.Drawing.Brushes]::Black, ($ML + 30), ($MT + 2))
  $g.FillRectangle((New-Object System.Drawing.SolidBrush $C_RED), ($ML + 8), ($MT + 24), 18, 6)
  $g.DrawString("PSRR-", $fontA, [System.Drawing.Brushes]::Black, ($ML + 30), ($MT + 18))
  Save-Canvas $bmp $outBase
  $g.Dispose(); $bmp.Dispose()
}

function Plot-Bars([string]$csvPath, [string]$outBase, [string]$title, [string]$xcol, [string]$ycol, [string]$ylab) {
  if (-not (Test-Path $csvPath)) { Write-Host "skip missing $csvPath"; return }
  $rows = @(Import-Csv $csvPath)
  if ($rows.Count -lt 1) { Write-Host "skip empty $csvPath"; return }
  # Accept alternate column names from different backends
  $ycands = @($ycol)
  if ($ycol -eq "ugf_mhz") { $ycands += @("gbw_mhz", "gbw", "ugf") }
  if ($ycol -eq "dcgain") { $ycands += @("gain", "Adc_dB", "adc") }
  $yuse = $null
  foreach ($c in $ycands) {
    if ($rows[0].PSObject.Properties.Name -contains $c) { $yuse = $c; break }
  }
  if (-not $yuse) { Write-Host "skip no y-col in $csvPath (want $ycol)"; return }
  $c = New-Canvas; $g = $c.g; $bmp = $c.bmp
  $fr = Draw-Frame $g $title "" $ylab
  $ys = $rows | ForEach-Object {
    $v = [double]($_."$yuse")
    if ($yuse -eq "gbw" -or $yuse -eq "ugf") { $v = $v / 1e6 }
    $v
  }
  $ymax = ($ys | Measure-Object -Maximum).Maximum
  if ($ymax -le 0) { $ymax = 1 }
  $n = $rows.Count
  $gap = 14
  $bw = [math]::Max(20, ($fr.pw - $gap * ($n + 1)) / $n)
  $brush = New-Object System.Drawing.SolidBrush $C_BLUE
  $penEdge = New-Object System.Drawing.Pen $C_BAR_EDGE, 1.0
  for ($i = 0; $i -lt $n; $i++) {
    $val = $ys[$i]
    $bh = $fr.ph * $val / $ymax
    $x = $ML + $gap + $i * ($bw + $gap)
    $y = $MT + $fr.ph - $bh
    $g.FillRectangle($brush, $x, $y, $bw, $bh)
    $g.DrawRectangle($penEdge, $x, $y, $bw, $bh)
    $lab = [string]$rows[$i]."$xcol"
    $sz = $g.MeasureString($lab, $fr.fontA)
    $g.DrawString($lab, $fr.fontA, [System.Drawing.Brushes]::Black, ($x + ($bw - $sz.Width) / 2), ($MT + $fr.ph + 6))
  }
  $g.DrawString(("{0:G4}" -f $ymax), $fr.fontA, [System.Drawing.Brushes]::Black, 4, ($MT - 2))
  Save-Canvas $bmp $outBase
  $g.Dispose(); $bmp.Dispose()
}

function Plot-Hist([string]$csvPath, [string]$outBase, [string]$title, [string]$xlabel, [double]$scale = 1.0) {
  if (-not (Test-Path $csvPath)) { Write-Host "skip missing $csvPath"; return }
  $rows = @(Import-Csv $csvPath)
  if ($rows.Count -lt 1) { Write-Host "skip empty $csvPath"; return }
  $names = @($rows[0].PSObject.Properties.Name)
  $counts = $null
  if ($names -contains "count") {
    $counts = @($rows | ForEach-Object { [double]$_.count })
    $nbins = $counts.Count
  } else {
    # Raw sample column (ugf / pm / ...) → fixed bins
    $valCol = $names | Where-Object { $_ -ne "run" } | Select-Object -First 1
    $vals = @($rows | ForEach-Object { [double]($_."$valCol") * $scale })
    $nbins = [math]::Min(20, [math]::Max(8, [int][math]::Ceiling([math]::Sqrt($vals.Count))))
    $vmin = ($vals | Measure-Object -Minimum).Minimum
    $vmax = ($vals | Measure-Object -Maximum).Maximum
    if ($vmax -eq $vmin) { $vmax = $vmin + 1 }
    $bw = ($vmax - $vmin) / $nbins
    $counts = @(0) * $nbins
    foreach ($v in $vals) {
      $idx = [int][math]::Floor(($v - $vmin) / $bw)
      if ($idx -ge $nbins) { $idx = $nbins - 1 }
      if ($idx -lt 0) { $idx = 0 }
      $counts[$idx]++
    }
  }
  $c = New-Canvas; $g = $c.g; $bmp = $c.bmp
  $fr = Draw-Frame $g $title $xlabel "Count"
  $cmax = ($counts | Measure-Object -Maximum).Maximum
  if ($cmax -le 0) { $cmax = 1 }
  $n = $counts.Count
  $bwPx = $fr.pw / [math]::Max($n, 1)
  $brush = New-Object System.Drawing.SolidBrush $C_BLUE
  $penEdge = New-Object System.Drawing.Pen $C_BAR_EDGE, 1.0
  for ($i = 0; $i -lt $n; $i++) {
    $ct = [double]$counts[$i]
    $bh = $fr.ph * $ct / $cmax
    $x = $ML + $i * $bwPx
    $y = $MT + $fr.ph - $bh
    $g.FillRectangle($brush, $x, $y, [math]::Max(1, $bwPx - 1), $bh)
    $g.DrawRectangle($penEdge, $x, $y, [math]::Max(1, $bwPx - 1), $bh)
  }
  Save-Canvas $bmp $outBase
  $g.Dispose(); $bmp.Dispose()
}

function Resolve-PsrrPair([string]$dir) {
  $p = Join-Path $dir "psrr_p.dat"; $n = Join-Path $dir "psrr_n.dat"
  if (-not (Test-Path $p)) { $p = Join-Path $dir "psrrp.dat" }
  if (-not (Test-Path $n)) { $n = Join-Path $dir "psrrn.dat" }
  return @{ p = $p; n = $n }
}

function Render-Backend([string]$figDir, [string]$label) {
  if (-not (Test-Path $figDir)) { Write-Host "skip missing backend $label"; return }
  Plot-LogLine (Join-Path $figDir "bode_mag.dat") (Join-Path $figDir "bode_mag") "$label Bode magnitude" "Gain (dB)" $C_BLUE $LW_MAIN
  Plot-LogLine (Join-Path $figDir "bode_phase.dat") (Join-Path $figDir "bode_phase") "$label Bode phase" "Phase (rad)" $C_RED $LW_MAIN
  Plot-LogLine (Join-Path $figDir "cmrr.dat") (Join-Path $figDir "cmrr") "$label CMRR path" "Gain (dB)" $C_BLUE $LW_MAIN
  $ps = Resolve-PsrrPair $figDir
  if ((Test-Path $ps.p) -and (Test-Path $ps.n)) {
    Plot-PsrrOverlay $ps.p $ps.n (Join-Path $figDir "psrr") "$label PSRR+/PSRR-"
  }
  Plot-LogLine (Join-Path $figDir "noise.dat") (Join-Path $figDir "noise") "$label input-referred noise" "en (V/rtHz)" $C_PURPLE $LW_MAIN
  # Titles: ASCII only (no em-dash) -- System.Drawing + wrong console code page mojibake CJK
  Plot-Bars (Join-Path $figDir "corners.csv") (Join-Path $figDir "corners_ugf") "$label corners - UGF" "corner" "ugf_mhz" "UGF (MHz)"
  Plot-Bars (Join-Path $figDir "corners.csv") (Join-Path $figDir "corners_gain") "$label corners - DC gain" "corner" "dcgain" "Gain (dB)"
  Plot-Hist (Join-Path $figDir "mc_ugf_hist.csv") (Join-Path $figDir "mc_ugf_hist") "$label MC UGF histogram" "UGF (MHz)" 1e-6
  Plot-Hist (Join-Path $figDir "mc_pm_hist.csv") (Join-Path $figDir "mc_pm_hist") "$label MC PM histogram" "PM (deg)" 1.0
}

$run = (Resolve-Path $RunDir).Path
Render-Backend (Join-Path $run "cmos\figures") "CMOS"
Render-Backend (Join-Path $run "sky130\figures") "sky130"
Render-Backend (Join-Path $run "ihp\figures") "IHP"
Render-Backend (Join-Path $run "gf180\figures") "GF180"

$cross = Join-Path $run "figures_cross.csv"
$crossOut = Join-Path $run "figures"
if (-not (Test-Path $crossOut)) { New-Item -ItemType Directory -Force -Path $crossOut | Out-Null }
Plot-Bars $cross (Join-Path $crossOut "cross_ugf") "Cross-backend UGF" "backend" "ugf_mhz" "UGF (MHz)"
Plot-Bars $cross (Join-Path $crossOut "cross_gain") "Cross-backend DC gain" "backend" "dcgain" "Gain (dB)"
Plot-Bars $cross (Join-Path $crossOut "cross_pm") "Cross-backend PM" "backend" "pm_deg" "PM (deg)"
Plot-Bars $cross (Join-Path $crossOut "cross_power") "Cross-backend power" "backend" "power_mw" "P (mW)"
# also keep copies at run root for older report paths
Plot-Bars $cross (Join-Path $run "cross_ugf") "Cross-backend UGF" "backend" "ugf_mhz" "UGF (MHz)"
Plot-Bars $cross (Join-Path $run "cross_gain") "Cross-backend DC gain" "backend" "dcgain" "Gain (dB)"
Plot-Bars $cross (Join-Path $run "cross_pm") "Cross-backend PM" "backend" "pm_deg" "PM (deg)"
Plot-Bars $cross (Join-Path $run "cross_power") "Cross-backend power" "backend" "power_mw" "P (mW)"

Write-Host "dev-plot style render complete"
