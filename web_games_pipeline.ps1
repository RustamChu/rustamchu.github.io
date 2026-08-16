# ==================================================================
#  ИГРЫ -> БРАУЗЕР: сборка wasm-версий семи pygame-игр (pygbag)  v2
#  Результат: site\play\<игра>\  — после publish_site.ps1 кнопки
#  «ИГРАТЬ ПРЯМО ЗДЕСЬ» на сайте появятся у этих игр сами.
# ==================================================================
$ErrorActionPreference = "Continue"
trap { Write-Host ""; Write-Host "ОШИБКА: $_" -ForegroundColor Red; Read-Host "Enter - закрыть"; exit 1 }

if (-not $PSScriptRoot) { Write-Host "Запустите сам файл скрипта."; Read-Host; exit 1 }
$root = Split-Path $PSScriptRoot -Parent   # ...\portfolio_plays
$site = $PSScriptRoot                       # ...\portfolio_plays\site

# --- python: сначала стабильные версии, 3.14 - в последнюю очередь ---
$py = $null
foreach ($cand in @("py -3.12", "py -3.11", "py -3.13", "py -3.10", "py -3", "python", "python3")) {
    $v = & cmd /c "$cand --version" 2>&1
    if ($LASTEXITCODE -eq 0) { $py = $cand; $pyver = ($v | Out-String).Trim(); break }
}
if (-not $py) {
    Write-Host "Python не найден." -ForegroundColor Red
    Read-Host "Enter - закрыть"; exit 1
}
Write-Host "Python: $py  ($pyver)" -ForegroundColor Cyan

# --- pygbag: ставим при необходимости, проверяем через pip show + import ---
$null = & cmd /c "$py -m pip show pygbag" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ставлю pygbag (конвертер pygame -> браузер)..." -ForegroundColor Cyan
    $null = & cmd /c "$py -m pip install --user --no-warn-script-location -q pygbag" 2>&1
    $null = & cmd /c "$py -m pip show pygbag" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "pip не смог поставить pygbag - пришлите вывод:" -ForegroundColor Red
        & cmd /c "$py -m pip install --user pygbag"
        Read-Host "Enter - закрыть"; exit 1
    }
}
Write-Host "pygbag установлен." -ForegroundColor Green

# --- совместимость: pygbag должен импортироваться этим Python ---
$null = & cmd /c "$py -c `"import pygbag`"" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "pygbag не подружился с этим Python ($pyver) - он слишком новый." -ForegroundColor Yellow
    Write-Host "Решение: поставить рядом Python 3.12 (займёт минуту), скрипт сам его подхватит."
    $a = Read-Host "Поставить Python 3.12 сейчас через winget? (Enter - да, N - нет)"
    if ($a -ne "N" -and $a -ne "n") {
        & winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        Write-Host ""
        Write-Host "Готово. Запустите этот скрипт ещё раз - он выберет py -3.12 сам." -ForegroundColor Green
    }
    Read-Host "Enter - закрыть"; exit 0
}


# --- тач-геймпад: вставляется в wasm-страницу каждой игры ---
$pad = @'
<style>
  #tpad{display:none;position:fixed;inset:auto 0 0 0;z-index:99;padding:10px 12px 14px;
    pointer-events:none;user-select:none;-webkit-user-select:none}
  @media (pointer:coarse){#tpad{display:flex;justify-content:space-between;align-items:flex-end}}
  #tpad .grp{display:flex;gap:9px;align-items:flex-end;pointer-events:auto}
  #tpad .dpad{display:grid;justify-items:center;gap:8px}
  #tpad .dpad .row{display:flex;gap:8px}
  #tpad button{min-width:54px;height:54px;border-radius:13px;border:1px solid rgba(140,160,220,.4);
    background:rgba(16,20,36,.72);color:#dfe6f5;font:700 17px/1 system-ui;touch-action:none;
    -webkit-tap-highlight-color:transparent}
  #tpad button:active{background:rgba(70,90,160,.6)}
  #tpad button.big{min-width:82px;height:66px;border-radius:16px}
  #tpad .mini{position:fixed;top:8px;right:10px;display:flex;gap:7px;pointer-events:auto}
  #tpad .mini button{min-width:44px;height:36px;font-size:11px;border-radius:8px}
</style>
<div id="tapstart" style="position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:98;pointer-events:none">
  <div style="background:rgba(8,11,22,.88);border:1px solid #4de3e3;border-radius:14px;padding:16px 22px;color:#cfeaf4;font:700 16px/1.5 system-ui;text-align:center;box-shadow:0 0 30px rgba(77,227,227,.25)">
    &#9654; ТАПНИТЕ ПО ЭКРАНУ,<br>ЧТОБЫ ЗАПУСТИТЬ ИГРУ<br>
    <span style="font-weight:400;font-size:12px;color:#8f9ab8">первая загрузка — до минуты, дальше быстро</span>
  </div>
</div>
<div id="tpad">
  <div class="mini">
    <button data-code="Enter">ENTER</button><button data-code="KeyR">R</button>
    <button data-code="KeyH">H</button><button data-code="Escape">ESC</button>
  </div>
  <div class="grp dpad">
    <button data-code="ArrowUp">&#9650;</button>
    <div class="row">
      <button data-code="ArrowLeft">&#9664;</button>
      <button data-code="ArrowDown">&#9660;</button>
      <button data-code="ArrowRight">&#9654;</button>
    </div>
  </div>
  <div class="grp">
    <button data-code="ShiftLeft">SHIFT</button>
    <button data-code="KeyE">E</button>
    <button class="big" data-code="Space">ПРОБЕЛ</button>
  </div>
</div>
<script>
(function(){
  var ts=document.getElementById("tapstart");
  function hideTs(){ if(ts){ ts.remove(); ts=null; } }
  addEventListener("pointerdown",hideTs,{capture:true});
  addEventListener("keydown",hideTs,{capture:true});
  setTimeout(hideTs,25000);
  function fire(type,code){
    try{ dispatchEvent(new KeyboardEvent(type,{code:code,key:code,bubbles:true})); }catch(e){}
    try{ var c=document.querySelector("canvas");
      if(c) c.dispatchEvent(new KeyboardEvent(type,{code:code,key:code,bubbles:true})); }catch(e){}
  }
  document.querySelectorAll("#tpad [data-code]").forEach(function(b){
    var code=b.getAttribute("data-code");
    b.addEventListener("pointerdown",function(e){ e.preventDefault(); b.setPointerCapture&&b.setPointerCapture(e.pointerId); fire("keydown",code); });
    b.addEventListener("pointerup",function(e){ e.preventDefault(); fire("keyup",code); });
    b.addEventListener("pointercancel",function(){ fire("keyup",code); });
    b.addEventListener("contextmenu",function(e){ e.preventDefault(); });
  });
})();
</script>
'@

$games = @("neon-doom","ashen-depths","last-reactor","orbit-nine","bathysphere","zimnik","medvezhatnik")
$wrapper = @'
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_main


async def _run():
    game = game_main.Game()
    while getattr(game, "running", True):
        game.step()
        await asyncio.sleep(0)


asyncio.run(_run())
'@

$done = @(); $fail = @()
foreach ($g in $games) {
    $src = Join-Path $root $g
    if (-not (Test-Path (Join-Path $src "main.py"))) {
        Write-Host "[$g] пропуск: нет main.py в $src" -ForegroundColor Yellow
        $fail += $g; continue
    }
    Write-Host ""
    Write-Host "=== $g ===" -ForegroundColor Cyan
    $tmp = Join-Path $site "_websrc\$g"
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    Copy-Item (Join-Path $src "*.py") $tmp
    Rename-Item (Join-Path $tmp "main.py") "game_main.py"
    Set-Content -Path (Join-Path $tmp "main.py") -Value $wrapper -Encoding UTF8

    Write-Host "[$g] сборка wasm (первый раз докачает шаблон)..."
    $out = & cmd /c "$py -m pygbag --build `"$tmp`"" 2>&1
    $web = Join-Path $tmp "build\web"
    if (Test-Path (Join-Path $web "index.html")) {
        $dst = Join-Path $site "play\$g"
        if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
        New-Item -ItemType Directory -Path $dst -Force | Out-Null
        Copy-Item (Join-Path $web "*") $dst -Recurse
        # тач-геймпад для телефонов
        $idxPath = Join-Path $dst "index.html"
        if (Test-Path $idxPath) {
            $html = Get-Content $idxPath -Raw -Encoding UTF8
            if ($html -notmatch "tpad") {
                if ($html -match "</body>") { $html = $html -replace "</body>", ($pad + "`n</body>") }
                else { $html = $html + $pad }
                Set-Content -Path $idxPath -Value $html -Encoding UTF8
            }
        }
        Write-Host "[$g] ГОТОВО (с тач-кнопками) -> site\play\$g" -ForegroundColor Green
        $done += $g
    } else {
        Write-Host "[$g] сборка не удалась, хвост вывода:" -ForegroundColor Red
        Write-Host (($out | Select-Object -Last 15) | Out-String)
        $fail += $g
    }
}

Write-Host ""
Write-Host ("Собрано: " + $done.Count + " из " + $games.Count) -ForegroundColor $(if ($fail.Count -eq 0) { "Green" } else { "Yellow" })
if ($done.Count -gt 0) {
    Write-Host "Дальше: publish_site.ps1 - и кнопки ИГРАТЬ появятся на сайте сами." -ForegroundColor Cyan
}
if ($fail.Count -gt 0) {
    Write-Host ("Не собрались: " + ($fail -join ", ") + " - пришлите вывод, разберём.") -ForegroundColor Yellow
}
Read-Host "Enter - закрыть"
