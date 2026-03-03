# fetch_plugin.ps1 — Download the latest plugin zip from GitHub Releases
#
# No GitHub token required — release assets on public repos are publicly accessible.
#
# Usage:
#   scripts\fetch_plugin.ps1 [options]
#
# Options:
#   -Tag   Release tag to download  (default: latest)
#          Example: v1.2.3
#
# Output:
#   Plugin zip is saved to:  dist\loom_qgis_plugin.zip
#   Install it directly in QGIS via Plugins > Manage and Install Plugins > Install from ZIP.

param(
    [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"

$Owner      = "jordiMartinB"
$Repo       = "loom-qgis-plugin"
$AssetName  = "loom_qgis_plugin.zip"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
$DistDir   = Join-Path $RepoRoot "dist"
$OutFile   = Join-Path $DistDir $AssetName

$Headers = @{
    Accept                 = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

$BaseApi = "https://api.github.com/repos/$Owner/$Repo"

# ---------------------------------------------------------------------------
# Resolve the release
# ---------------------------------------------------------------------------
if ($Tag -eq "latest") {
    $ReleaseUrl = "$BaseApi/releases/latest"
    Write-Host "Fetching latest release..."
} else {
    $ReleaseUrl = "$BaseApi/releases/tags/$Tag"
    Write-Host "Fetching release '$Tag'..."
}

$Release = Invoke-RestMethod -Uri $ReleaseUrl -Headers $Headers
Write-Host "  Release: $($Release.tag_name)  '$($Release.name)'"
Write-Host "  Published: $($Release.published_at)"

# ---------------------------------------------------------------------------
# Find the plugin zip asset
# ---------------------------------------------------------------------------
$Asset = $Release.assets | Where-Object { $_.name -eq $AssetName } | Select-Object -First 1

if ($null -eq $Asset) {
    Write-Host ""
    Write-Error "ERROR: Asset '$AssetName' not found in release $($Release.tag_name)."
    Write-Host "Available assets:"
    $Release.assets | ForEach-Object { Write-Host "  - $($_.name)" }
    exit 1
}

Write-Host "  Asset: $($Asset.name)  size=$([math]::Round($Asset.size/1KB)) KB"

# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------
if (-not (Test-Path $DistDir)) {
    New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
}

Write-Host "Downloading to: $OutFile"
Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $OutFile

Write-Host ""
Write-Host "Done: $OutFile"
Write-Host "Install in QGIS via: Plugins > Manage and Install Plugins > Install from ZIP"
