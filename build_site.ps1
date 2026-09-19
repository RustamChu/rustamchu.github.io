# ==============================================================
#  СБОРКА САЙТА (запускается сама из publish_site.ps1)
#   1) штамп версии в шапке index.html
#   2) VERSION в sw.js  -> кэш инвалидируется сам
#   3) карточка для соцсетей og.png 1200x630 рисуется заново
#  Ноль внешних зависимостей: только .NET, который уже есть в Windows.
# ==============================================================
$ErrorActionPreference = "Stop"
if (-not $PSScriptRoot) { Write-Host "Запустите файл, а не вставляйте текст." -ForegroundColor Yellow; exit 1 }
Set-Location $PSScriptRoot

$now   = Get-Date
$stamp = "v" + $now.ToString("dd.MM HH:mm") + " МСК"
$ver   = $now.ToString("dd.MM-HHmm")
$utf8  = New-Object System.Text.UTF8Encoding($false)

# ---------- 1. штамп в шапке ----------
$idxPath = Join-Path $PSScriptRoot "index.html"
$idx = [System.IO.File]::ReadAllText($idxPath, $utf8)
$idx = [regex]::Replace($idx, '(?<=id="bstamp"[^>]*>)[^<]*', $stamp)
[System.IO.File]::WriteAllText($idxPath, $idx, $utf8)
Write-Host "  штамп:  $stamp" -ForegroundColor DarkGray

# ---------- 2. версия кэша ----------
$swPath = Join-Path $PSScriptRoot "sw.js"
$sw = [System.IO.File]::ReadAllText($swPath, $utf8)
$sw = [regex]::Replace($sw, '(?<=const VERSION = ")[^"]*', $ver)
[System.IO.File]::WriteAllText($swPath, $sw, $utf8)
Write-Host "  кэш:    $ver" -ForegroundColor DarkGray

# ---------- 3. карточка для соцсетей ----------
Add-Type -AssemblyName System.Drawing
$W = 1200; $H = 630
$C  = { param($hex) [System.Drawing.ColorTranslator]::FromHtml($hex) }
$BG=&$C "#0a0d1a"; $PANEL=&$C "#12172b"; $LINE=&$C "#232b4a"
$CY=&$C "#4de3e3"; $MG=&$C "#ff4d8d"; $GOLD=&$C "#ffc94d"; $TXT=&$C "#e8ecf6"; $DIM=&$C "#8f9ab8"

$bmp = New-Object System.Drawing.Bitmap($W, $H)
$g   = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode     = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

$rectAll = New-Object System.Drawing.Rectangle(0,0,$W,$H)
$bgBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush($rectAll, $BG, $PANEL, 90)
$g.FillRectangle($bgBrush, $rectAll)
$barRect = New-Object System.Drawing.Rectangle(0,0,$W,9)
$barBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush($barRect, $CY, $MG, 0)
$g.FillRectangle($barBrush, $barRect)

$px = [System.Drawing.GraphicsUnit]::Pixel
$B  = [System.Drawing.FontStyle]::Bold
$fLogo  = New-Object System.Drawing.Font("Segoe UI", 34, $B, $px)
$fTitle = New-Object System.Drawing.Font("Segoe UI", 82, $B, $px)
$fSub   = New-Object System.Drawing.Font("Segoe UI", 27, [System.Drawing.FontStyle]::Regular, $px)
$fNum   = New-Object System.Drawing.Font("Consolas", 46, $B, $px)
$fLab   = New-Object System.Drawing.Font("Segoe UI", 19, [System.Drawing.FontStyle]::Regular, $px)
$fSite  = New-Object System.Drawing.Font("Segoe UI", 30, $B, $px)
$fStamp = New-Object System.Drawing.Font("Consolas", 20, [System.Drawing.FontStyle]::Regular, $px)

$bTxt=New-Object System.Drawing.SolidBrush($TXT); $bCy=New-Object System.Drawing.SolidBrush($CY)
$bDim=New-Object System.Drawing.SolidBrush($DIM); $bGold=New-Object System.Drawing.SolidBrush($GOLD)
$bPanel=New-Object System.Drawing.SolidBrush($PANEL); $pLine=New-Object System.Drawing.Pen($LINE,2)

$g.DrawString("RUSTAM", $fLogo, $bTxt, 60, 50)
$wLogo = $g.MeasureString("RUSTAM", $fLogo).Width
$g.DrawString(".CHU", $fLogo, $bCy, (60 + $wLogo - 12), 50)
$g.DrawString("ЧУЧУЕВ РУСТАМ", $fTitle, $bTxt, 58, 145)
$g.DrawString("ПОРТФОЛИО · САЙТЫ, ИНТЕРФЕЙСЫ, ИНСТРУМЕНТЫ", $fSub, $bDim, 62, 265)
$g.DrawLine($pLine, 64, 340, 1136, 340)

function New-RoundRect([int]$x,[int]$y,[int]$w,[int]$h,[int]$r){
  $p = New-Object System.Drawing.Drawing2D.GraphicsPath
  $p.AddArc($x, $y, $r*2, $r*2, 180, 90)
  $p.AddArc($x+$w-$r*2, $y, $r*2, $r*2, 270, 90)
  $p.AddArc($x+$w-$r*2, $y+$h-$r*2, $r*2, $r*2, 0, 90)
  $p.AddArc($x, $y+$h-$r*2, $r*2, $r*2, 90, 90)
  $p.CloseFigure(); return $p
}
$stats = @(@("16","СТЕНДОВ"), @("8","СТИЛЕЙ"), @("0","БИБЛИОТЕК"), @("1","ФАЙЛ"))
$x = 64
foreach ($st in $stats) {
  $path = New-RoundRect $x 378 250 120 16
  $g.FillPath($bPanel, $path); $g.DrawPath($pLine, $path); $path.Dispose()
  $g.DrawString($st[0], $fNum,  $bGold, ($x+18), 396)
  $g.DrawString($st[1], $fLab,  $bDim,  ($x+20), 456)
  $x += 274
}
$g.DrawString("rustamchu.ru", $fSite, $bCy, 60, 552)
$note = "ОДИН ФАЙЛ · НОЛЬ БИБЛИОТЕК"
$wNote = $g.MeasureString($note, $fLab).Width
$g.DrawString($note, $fLab, $bDim, (($W - $wNote) / 2), 562)
$wStamp = $g.MeasureString($stamp, $fStamp).Width
$g.DrawString($stamp, $fStamp, $bDim, (1140 - $wStamp), 560)

$ogPath = Join-Path $PSScriptRoot "og.png"
$bmp.Save($ogPath, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Host "  карточка: og.png 1200x630" -ForegroundColor DarkGray
