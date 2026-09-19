# ==============================================================
#  ЗАЛИВКА САЙТА: GitHub Pages -> https://rustamchu.github.io
#  Домен rustamchu.ru подключается после первого пуша (см. чат)
#  Запуск: правой кнопкой -> "Выполнить с помощью PowerShell"
# ==============================================================
$ErrorActionPreference = "Continue"
trap { Write-Host ""; Write-Host "ОШИБКА: $_" -ForegroundColor Red; Read-Host "Enter - закрыть"; exit 1 }

if (-not $PSScriptRoot) {
    Write-Host "Запустите сам файл publish_site.ps1 (не вставляйте текст в окно)." -ForegroundColor Yellow
    Read-Host "Enter - закрыть"; exit 1
}
Set-Location $PSScriptRoot

if (-not (Test-Path "index.html")) {
    Write-Host "Рядом со скриптом нет index.html - положите его в эту папку." -ForegroundColor Red
    Read-Host "Enter - закрыть"; exit 1
}

$null = & git --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "git не найден. Поставьте Git for Windows: https://git-scm.com/download/win" -ForegroundColor Red
    Start-Process "https://git-scm.com/download/win"
    Read-Host "Enter - закрыть"; exit 1
}

# ---------- СБОРКА: штамп, версия кэша, карточка соцсетей ----------
Write-Host "Собираю..." -ForegroundColor Cyan
$build = Join-Path $PSScriptRoot "build_site.ps1"
if (Test-Path $build) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Сборка не прошла - публикация отменена." -ForegroundColor Red
        Read-Host "Enter - закрыть"; exit 1
    }
} else {
    Write-Host "build_site.ps1 рядом не найден - публикую как есть." -ForegroundColor Yellow
}

$repo = "rustamchu.github.io"
$url  = "https://github.com/RustamChu/$repo.git"

# CNAME - чтобы Pages знал про домен rustamchu.ru
Set-Content -Path "CNAME" -Value "rustamchu.ru" -Encoding Ascii

if (-not (Test-Path ".git")) {
    $null = & git init 2>&1
}
$null = & git checkout -B main 2>&1
$null = & git remote remove origin 2>&1
$null = & git remote add origin $url 2>&1
$null = & git rm -r --cached _websrc 2>&1
$null = & git add -A 2>&1
$null = & git commit -m ("site " + (Get-Date -Format "yyyy-MM-dd HH:mm")) 2>&1

Write-Host "Пушу на $url ..." -ForegroundColor Cyan
$out = & git push -u origin main 2>&1
$txt = ($out | Out-String)

if ($LASTEXITCODE -ne 0 -and $txt -match "Repository not found") {
    Write-Host ""
    Write-Host "Репозитория ещё нет. Открываю страницу создания:" -ForegroundColor Yellow
    Write-Host "  имя: $repo   /   Public   /   БЕЗ галочек README и прочего" -ForegroundColor Yellow
    Start-Process "https://github.com/new?name=$repo&visibility=public"
    Read-Host "Создали? Enter - пробую пуш ещё раз"
    $out = & git push -u origin main 2>&1
    $txt = ($out | Out-String)
}
if ($LASTEXITCODE -ne 0 -and $txt -match "rejected") {
    Write-Host "На GitHub есть более свежие коммиты - подтягиваю и пробую снова..." -ForegroundColor Yellow
    $null = & git pull --rebase origin main 2>&1
    $out = & git push -u origin main 2>&1
    $txt = ($out | Out-String)
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "ГОТОВО." -ForegroundColor Green
    Write-Host "Через 1-2 минуты сайт откроется: https://rustamchu.github.io" -ForegroundColor Green
    Write-Host ""
    Write-Host "Подключение домена rustamchu.ru (один раз):" -ForegroundColor Cyan
    Write-Host "  1) На GitHub: репозиторий $repo -> Settings -> Pages"
    Write-Host "     Custom domain: rustamchu.ru -> Save (файл CNAME уже в репо)"
    Write-Host "  2) У регистратора домена, в DNS-записях:"
    Write-Host "     A     @    185.199.108.153"
    Write-Host "     A     @    185.199.109.153"
    Write-Host "     A     @    185.199.110.153"
    Write-Host "     A     @    185.199.111.153"
    Write-Host "     CNAME www  rustamchu.github.io"
    Write-Host "  3) Подождать до часа и включить Enforce HTTPS в Settings -> Pages"
} else {
    Write-Host $txt -ForegroundColor Red
    Write-Host "Если открылось окно входа GitHub - войдите и запустите скрипт снова." -ForegroundColor Yellow
}
Read-Host "Enter - закрыть"
