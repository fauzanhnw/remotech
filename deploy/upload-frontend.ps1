# Remotech - build & upload frontend ke VPS. Jalankan dari mana saja di dalam repo:
#   .\deploy\upload-frontend.ps1 -VpsIp 1.2.3.4
# Opsional: -VpsUser deploy (default), -SkipBuild bila dist/ sudah siap.
param(
    [Parameter(Mandatory = $true)]
    [string]$VpsIp,

    [string]$VpsUser = "deploy",

    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$webDir = Join-Path (Split-Path $PSScriptRoot -Parent) "remotech-web"
$envFile = Join-Path $webDir ".env"

Write-Host "==> Cek remotech-web/.env (build-time)" -ForegroundColor Cyan
if (-not (Test-Path $envFile)) {
    Write-Host "    $envFile tidak ditemukan. Membuat dari .env.example..." -ForegroundColor Yellow
    Copy-Item (Join-Path $webDir ".env.example") $envFile
}
$envContent = Get-Content $envFile -Raw
if ($envContent -notmatch "VITE_API_BASE_URL=https://api\.") {
    Write-Host "    WARNING: VITE_API_BASE_URL di $envFile belum produksi." -ForegroundColor Yellow
    Write-Host "    Untuk VPS, isi: VITE_API_BASE_URL=https://api.remotech.web.id" -ForegroundColor Yellow
    Write-Host "    Dan: VITE_MIDTRANS_CLIENT_KEY=<Mid-client-...>" -ForegroundColor Yellow
    $continue = Read-Host "    Tetap build dengan .env saat ini? (y/N)"
    if ($continue -ne "y") { exit 1 }
}

if (-not $SkipBuild) {
    Write-Host "==> npm install + build" -ForegroundColor Cyan
    Push-Location $webDir
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install gagal" }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "npm run build gagal" }
    }
    finally { Pop-Location }
}

$distDir = Join-Path $webDir "dist"
if (-not (Test-Path (Join-Path $distDir "index.html"))) {
    throw "dist/index.html tidak ditemukan - build dulu atau jalankan tanpa -SkipBuild"
}

Write-Host "==> Upload dist/ ke ${VpsUser}@${VpsIp}:/tmp/dist/" -ForegroundColor Cyan
$target = "${VpsUser}@${VpsIp}:/tmp/dist/"
scp -r (Join-Path $distDir "*") $target
if ($LASTEXITCODE -ne 0) { throw "scp gagal" }

Write-Host ""
Write-Host "Upload selesai. Sekarang di VPS (ssh ${VpsUser}@${VpsIp}), jalankan:" -ForegroundColor Green
Write-Host "  sudo mkdir -p /var/www/remotech"
Write-Host "  sudo cp -r /tmp/dist/* /var/www/remotech/"
Write-Host "  sudo chown -R ${VpsUser}:www-data /var/www/remotech"
Write-Host "  sudo chmod -R o+rX /var/www/remotech"
