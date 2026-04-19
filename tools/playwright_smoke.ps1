param(
  [string]$BaseUrl = "http://localhost:8080",
  [string]$OutDir = "output\\playwright"
)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$cacheDir = Join-Path (Get-Location) ".npm-cache"
$browserDir = Join-Path (Get-Location) ".playwright-browsers"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
New-Item -ItemType Directory -Force -Path $browserDir | Out-Null
$env:npm_config_cache = $cacheDir
$env:PLAYWRIGHT_BROWSERS_PATH = $browserDir

$pages = @(
  "/login",
  "/",
  "/cari",
  "/stok",
  "/kasa",
  "/cekler",
  "/mutabakat",
  "/tahsilat-oneri",
  "/karlilik"
)

foreach ($p in $pages) {
  $url = "$BaseUrl$p"
  $name = ($p.TrimStart('/') -replace '/', '_')
  if ([string]::IsNullOrWhiteSpace($name)) { $name = "dashboard" }
  $shot = Join-Path $OutDir "$name.png"
  npx.cmd --cache "$cacheDir" -y playwright screenshot $url $shot
  if ($LASTEXITCODE -ne 0) {
    Write-Host "HATA: screenshot alinamadi -> $url"
  }
}

Write-Host "Playwright smoke tamamlandi: $OutDir"
