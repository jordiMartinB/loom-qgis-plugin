#!/usr/bin/env bash
# build_plugin_zip.sh — Package the QGIS plugin as distributable .zip files
#
# Usage:
#   scripts/build_plugin_zip.sh [PYTHON_TAG [VERSION]]
#
# PYTHON_TAG  selects which wheels to bundle (default: cp312).
# VERSION     string appended to the zip name  (default: empty).
#             Typically the git tag, e.g. "v0.1.1".
#
# Outputs:
#   dist/loom_qgis_plugin_linux[_VERSION].zip   — Linux (manylinux) package
#   dist/loom_qgis_plugin_windows[_VERSION].zip — Windows (win_amd64) package
#
# Each zip unzips to a single top-level folder `loom_qgis_plugin/` which QGIS
# places in its plugins directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PYTHON_TAG="${1:-cp312}"
VERSION="${2:-}"          # e.g. "v0.1.1"  (empty → no suffix)

WHEELHOUSE="$REPO_ROOT/wheelhouse"
DIST_DIR="$REPO_ROOT/dist"
PLUGIN_NAME="loom_qgis_plugin"

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

# ---------------------------------------------------------------------------
# build_package <platform> <wheel_glob> <ext_glob> <platform_suffix>
# ---------------------------------------------------------------------------
build_package() {
    local platform="$1"
    local wheel_glob="$2"
    local ext_glob="$3"
    local platform_suffix="$4"

    # Compose output zip name:  loom_qgis_plugin_linux_cp312_v0.1.1.zip
    local zip_label="${PLUGIN_NAME}_${platform_suffix}_${PYTHON_TAG}"
    [[ -n "$VERSION" ]] && zip_label="${zip_label}_${VERSION}"

    echo ""
    echo "=== Building $platform package: ${zip_label}.zip ==="

    # Find wheel
    local WHEEL
    WHEEL=$(find "$WHEELHOUSE" -name "$wheel_glob" | sort | tail -1)
    if [[ -z "$WHEEL" ]]; then
        echo "WARNING: no $platform wheel matching '${PYTHON_TAG}' found in $WHEELHOUSE — skipping" >&2
        echo "Available wheels:" >&2
        ls "$WHEELHOUSE" >&2
        return 0
    fi
    echo "Using wheel: $(basename "$WHEEL")"

    # Set up staging directory
    local STAGING="$DIST_DIR/${PLUGIN_NAME}"
    rm -rf "$STAGING"
    mkdir -p "$STAGING/lib"

    # Unpack wheel
    local UNPACK_TMP="$DIST_DIR/_wheel_unpack"
    rm -rf "$UNPACK_TMP"
    mkdir -p "$UNPACK_TMP"
    python3 - <<EOF
import zipfile
with zipfile.ZipFile("$WHEEL") as z:
    z.extractall("$UNPACK_TMP")
EOF

    # Copy extension module (.so or .pyd)
    local EXT
    EXT=$(find "$UNPACK_TMP" -maxdepth 2 -name "$ext_glob" | head -1)
    if [[ -z "$EXT" ]]; then
        echo "ERROR: could not find '$ext_glob' in the $platform wheel" >&2
        rm -rf "$UNPACK_TMP" "$STAGING"
        return 1
    fi
    cp "$EXT" "$STAGING/lib/"
    echo "  + $(basename "$EXT")"

    # Copy bundled libs directory
    local LIBS_DIR
    LIBS_DIR=$(find "$UNPACK_TMP" -maxdepth 2 -type d -name "loom_python_plugin.libs" | head -1)
    if [[ -n "$LIBS_DIR" ]]; then
        cp -r "$LIBS_DIR" "$STAGING/lib/"
        echo "  + loom_python_plugin.libs/"
    fi

    rm -rf "$UNPACK_TMP"

    # Copy plugin source files
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

    # Create zip
    local ZIP_OUT="$DIST_DIR/${zip_label}.zip"
    rm -f "$ZIP_OUT"

    python3 - <<EOF
import zipfile
from pathlib import Path

staging  = Path("$STAGING")
zip_out  = Path("$ZIP_OUT")
dist_dir = Path("$DIST_DIR")

with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(staging.rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        arcname = path.relative_to(dist_dir)
        zf.write(path, arcname)

print(f"Plugin zip: {zip_out}")
print(f"Size: {zip_out.stat().st_size // 1024} KB")
EOF

    rm -rf "$STAGING"
}

mkdir -p "$DIST_DIR"

build_package \
    "linux" \
    "loom_python_plugin-*-${PYTHON_TAG}-*manylinux*.whl" \
    "loom.cpython-*.so" \
    "linux"

build_package \
    "windows" \
    "loom_python_plugin-*-${PYTHON_TAG}-*win_amd64*.whl" \
    "loom*.pyd" \
    "windows"

echo ""
echo "Done."
