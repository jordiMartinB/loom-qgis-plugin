#!/usr/bin/env bash
# build_plugin_zip.sh — Package the QGIS plugin as a distributable .zip
#
# Usage:
#   scripts/build_plugin_zip.sh [PYTHON_TAG]
#
# PYTHON_TAG selects which wheel to bundle the binary from (default: cp314).
# Examples:  cp310  cp311  cp312  cp313  cp314
#
# The output is:  dist/loom_qgis_plugin.zip
# It unzips to a single top-level folder `loom_qgis_plugin/` which QGIS
# places in its plugins directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PYTHON_TAG="${1:-cp314}"
WHEELHOUSE="$REPO_ROOT/wheelhouse"
DIST_DIR="$REPO_ROOT/dist"
PLUGIN_NAME="loom_qgis_plugin"
STAGING="$DIST_DIR/$PLUGIN_NAME"

# ---------------------------------------------------------------------------
# Find the matching wheel
# ---------------------------------------------------------------------------
WHEEL=$(find "$WHEELHOUSE" -name "loom_python_plugin-*-${PYTHON_TAG}-*.whl" | sort | tail -1)
if [[ -z "$WHEEL" ]]; then
    echo "ERROR: no wheel matching '${PYTHON_TAG}' found in $WHEELHOUSE" >&2
    echo "Available wheels:" >&2
    ls "$WHEELHOUSE" >&2
    exit 1
fi
echo "Using wheel: $(basename "$WHEEL")"

# ---------------------------------------------------------------------------
# Set up staging directory
# ---------------------------------------------------------------------------
rm -rf "$STAGING"
mkdir -p "$STAGING/lib"

# ---------------------------------------------------------------------------
# Unpack the wheel and extract the .so + bundled libs into lib/
# A .whl is a zip file; we use Python's zipfile module for portability.
# ---------------------------------------------------------------------------
UNPACK_TMP="$DIST_DIR/_wheel_unpack"
rm -rf "$UNPACK_TMP"
mkdir -p "$UNPACK_TMP"
python3 - <<EOF
import zipfile, sys
with zipfile.ZipFile("$WHEEL") as z:
    z.extractall("$UNPACK_TMP")
EOF

# Copy extension module  (loom.cpython-3xx-*.so)
SO=$(find "$UNPACK_TMP" -maxdepth 2 -name "loom.cpython-*.so" | head -1)
if [[ -z "$SO" ]]; then
    echo "ERROR: could not find loom.cpython-*.so in the wheel" >&2
    exit 1
fi
cp "$SO" "$STAGING/lib/"
echo "  + $(basename "$SO")"

# Copy bundled libs directory (loom_python_plugin.libs/)
LIBS_DIR=$(find "$UNPACK_TMP" -maxdepth 2 -type d -name "loom_python_plugin.libs" | head -1)
if [[ -n "$LIBS_DIR" ]]; then
    cp -r "$LIBS_DIR" "$STAGING/lib/"
    echo "  + loom_python_plugin.libs/"
fi

rm -rf "$UNPACK_TMP"

# ---------------------------------------------------------------------------
# Copy plugin source files
# ---------------------------------------------------------------------------
PLUGIN_FILES=(
    __init__.py
    plugin.py
    loom_algorithms.py
    loom_provider.py
    wrapper.py
    algorithm_config.json
    metadata.txt
)

PLUGIN_DIRS=(
    forms
    i18n
)

for f in "${PLUGIN_FILES[@]}"; do
    if [[ -f "$REPO_ROOT/$f" ]]; then
        cp "$REPO_ROOT/$f" "$STAGING/"
        echo "  + $f"
    else
        echo "WARNING: $f not found, skipping" >&2
    fi
done

for d in "${PLUGIN_DIRS[@]}"; do
    if [[ -d "$REPO_ROOT/$d" ]]; then
        cp -r "$REPO_ROOT/$d" "$STAGING/"
        echo "  + $d/"
    fi
done

# ---------------------------------------------------------------------------
# Create the zip  (QGIS expects: plugin_name/ at the top level)
# Uses Python's zipfile module to avoid requiring the `zip` system command.
# ---------------------------------------------------------------------------
ZIP_OUT="$DIST_DIR/${PLUGIN_NAME}.zip"
rm -f "$ZIP_OUT"

python3 - <<EOF
import zipfile, os
from pathlib import Path

staging = Path("$STAGING")
zip_out = Path("$ZIP_OUT")
dist_dir = Path("$DIST_DIR")

with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(staging.rglob("*")):
        # Skip __pycache__ and .pyc files
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        arcname = path.relative_to(dist_dir)
        zf.write(path, arcname)

print(f"Plugin zip: {zip_out}")
print(f"Size: {zip_out.stat().st_size // 1024} KB")
EOF
