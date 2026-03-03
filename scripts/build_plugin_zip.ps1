# build_plugin_zip.ps1 — Package the QGIS plugin as a distributable .zip
#
# Usage:
#   scripts\build_plugin_zip.ps1 [PYTHON_TAG]
#
# PYTHON_TAG selects which wheel to bundle the binary from (default: cp314).
# Examples:  cp310  cp311  cp312  cp313  cp314
#
# The output is:  dist\loom_qgis_plugin.zip
# It unzips to a single top-level folder `loom_qgis_plugin/` which QGIS
# places in its plugins directory.

param(
    [string]$PythonTag = "cp314"
)

$ErrorActionPreference = "Stop"

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot   = Split-Path -Parent $ScriptDir
$Wheelhouse = Join-Path $RepoRoot "wheelhouse"
$DistDir    = Join-Path $RepoRoot "dist"
$PluginName = "loom_qgis_plugin"
$Staging    = Join-Path $DistDir $PluginName

# ---------------------------------------------------------------------------
# Find the matching wheel
# ---------------------------------------------------------------------------
$Wheels = Get-ChildItem -Path $Wheelhouse -Filter "loom_python_plugin-*-${PythonTag}-*.whl" -ErrorAction SilentlyContinue |
          Sort-Object Name
if ($Wheels.Count -eq 0) {
    Write-Error "ERROR: no wheel matching '$PythonTag' found in $Wheelhouse"
    Write-Host "Available wheels:" -ForegroundColor Yellow
    Get-ChildItem -Path $Wheelhouse | Select-Object -ExpandProperty Name
    exit 1
}
$Wheel = $Wheels[-1].FullName
Write-Host "Using wheel: $(Split-Path -Leaf $Wheel)"

# ---------------------------------------------------------------------------
# Set up staging directory
# ---------------------------------------------------------------------------
if (Test-Path $Staging) { Remove-Item -Recurse -Force $Staging }
New-Item -ItemType Directory -Force -Path (Join-Path $Staging "lib") | Out-Null

# ---------------------------------------------------------------------------
# Unpack the wheel and extract the .pyd + bundled DLLs into lib/
# A .whl is a zip file; we use Python's zipfile module for portability.
# ---------------------------------------------------------------------------
$UnpackTmp = Join-Path $DistDir "_wheel_unpack"
if (Test-Path $UnpackTmp) { Remove-Item -Recurse -Force $UnpackTmp }
New-Item -ItemType Directory -Force -Path $UnpackTmp | Out-Null

python - @"
import zipfile
with zipfile.ZipFile(r"$Wheel") as z:
    z.extractall(r"$UnpackTmp")
"@

# Copy extension module  (loom.cpython-3xx-win_amd64.pyd)
$Pyd = Get-ChildItem -Path $UnpackTmp -Recurse -Depth 2 -Filter "loom.cpython-*.pyd" |
       Select-Object -First 1
if ($null -eq $Pyd) {
    Write-Error "ERROR: could not find loom.cpython-*.pyd in the wheel"
    exit 1
}
Copy-Item $Pyd.FullName -Destination (Join-Path $Staging "lib")
Write-Host "  + $($Pyd.Name)"

# Copy bundled DLLs directory (loom_python_plugin.libs/ or *.dist-info DLLs)
$LibsDir = Get-ChildItem -Path $UnpackTmp -Recurse -Depth 2 -Directory -Filter "loom_python_plugin.libs" |
           Select-Object -First 1
if ($null -ne $LibsDir) {
    Copy-Item $LibsDir.FullName -Destination (Join-Path $Staging "lib") -Recurse
    Write-Host "  + loom_python_plugin.libs/"
}

Remove-Item -Recurse -Force $UnpackTmp

# ---------------------------------------------------------------------------
# Copy plugin source files
# ---------------------------------------------------------------------------
$PluginFiles = @(
    "__init__.py",
    "plugin.py",
    "loom_algorithms.py",
    "loom_provider.py",
    "wrapper.py",
    "algorithm_config.json",
    "metadata.txt"
)

$PluginDirs = @(
    "forms",
    "i18n"
)

foreach ($f in $PluginFiles) {
    $Src = Join-Path $RepoRoot $f
    if (Test-Path $Src) {
        Copy-Item $Src -Destination $Staging
        Write-Host "  + $f"
    } else {
        Write-Warning "$f not found, skipping"
    }
}

foreach ($d in $PluginDirs) {
    $Src = Join-Path $RepoRoot $d
    if (Test-Path $Src) {
        Copy-Item $Src -Destination $Staging -Recurse
        Write-Host "  + $d/"
    }
}

# ---------------------------------------------------------------------------
# Create the zip  (QGIS expects: plugin_name/ at the top level)
# Uses Python's zipfile module to avoid requiring external zip tools.
# ---------------------------------------------------------------------------
$ZipOut = Join-Path $DistDir "${PluginName}.zip"
if (Test-Path $ZipOut) { Remove-Item -Force $ZipOut }

python - @"
import zipfile
from pathlib import Path

staging = Path(r"$Staging")
zip_out = Path(r"$ZipOut")
dist_dir = Path(r"$DistDir")

with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(staging.rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        arcname = path.relative_to(dist_dir)
        zf.write(path, arcname)

print(f"Plugin zip: {zip_out}")
print(f"Size: {zip_out.stat().st_size // 1024} KB")
"@
