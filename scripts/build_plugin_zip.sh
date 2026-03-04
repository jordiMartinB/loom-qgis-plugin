#!/usr/bin/env bash
# build_plugin_zip.sh — Package the QGIS plugin as distributable .zip files
#
# Usage:
#   scripts/build_plugin_zip.sh [VERSION [PYTHON_TAGS...]]
#
# VERSION      Version string appended to the zip name (default: empty).
#              Typically the git tag, e.g. "v0.1.1".
# PYTHON_TAGS  One or more Python tags to bundle (default: cp312 cp313 cp314).
#              Extensions for all tags are bundled into the same lib/ directory;
#              wrapper.py picks the right one at runtime.
#
# Outputs:
#   dist/loom_qgis_plugin_linux[_VERSION].zip   — Linux (manylinux) package
#   dist/loom_qgis_plugin_windows[_VERSION].zip — Windows (win_amd64) package

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VERSION="${1:-}"
shift || true
PYTHON_TAGS=("${@:-cp312 cp313 cp314}")
if [[ ${#PYTHON_TAGS[@]} -eq 1 && "${PYTHON_TAGS[0]}" == "cp312 cp313 cp314" ]]; then
    PYTHON_TAGS=(cp312 cp313 cp314)
fi

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
# build_package <platform_label> <wheel_glob_template> <ext_glob_template> <zip_suffix>
#
#   *_glob_template contains PYTAG as a placeholder replaced per Python tag.
# ---------------------------------------------------------------------------
build_package() {
    local platform="$1"
    local wheel_glob_tpl="$2"   # e.g. "loom_python_plugin-*-PYTAG-*manylinux*.whl"
    local ext_glob_tpl="$3"     # e.g. "loom*.so"
    local zip_suffix="$4"

    local zip_label="${PLUGIN_NAME}_${zip_suffix}"
    [[ -n "$VERSION" ]] && zip_label="${zip_label}_${VERSION}"

    echo ""
    echo "=== Building $platform package: ${zip_label}.zip ==="

    local STAGING="$DIST_DIR/${PLUGIN_NAME}"
    rm -rf "$STAGING"
    mkdir -p "$STAGING/lib"

    local found_any=0

    for PYTAG in "${PYTHON_TAGS[@]}"; do
        local wheel_glob="${wheel_glob_tpl/PYTAG/$PYTAG}"
        local WHEEL
        WHEEL=$(find "$WHEELHOUSE" -name "$wheel_glob" | sort | tail -1)
        if [[ -z "$WHEEL" ]]; then
            echo "  WARNING: no $platform wheel for $PYTAG — skipping" >&2
            continue
        fi
        echo "  $PYTAG: $(basename "$WHEEL")"

        local UNPACK_TMP="$DIST_DIR/_wheel_unpack_${PYTAG}"
        rm -rf "$UNPACK_TMP"
        mkdir -p "$UNPACK_TMP"
        python3 - <<EOF
import zipfile
with zipfile.ZipFile("$WHEEL") as z:
    z.extractall("$UNPACK_TMP")
EOF

        # Copy extension module
        local EXT
        EXT=$(find "$UNPACK_TMP" -name "${ext_glob_tpl/PYTAG/$PYTAG}" | head -1)
        if [[ -z "$EXT" ]]; then
            echo "  WARNING: extension not found in $PYTAG wheel (listing):" >&2
            find "$UNPACK_TMP" | sort >&2
            rm -rf "$UNPACK_TMP"
            continue
        fi
        cp "$EXT" "$STAGING/lib/"
        echo "    + $(basename "$EXT")"

        # Copy bundled libs (only once — they're the same for all versions)
        if [[ ! -d "$STAGING/lib/loom_python_plugin.libs" ]]; then
            local LIBS_DIR
            LIBS_DIR=$(find "$UNPACK_TMP" -maxdepth 2 -type d -name "loom_python_plugin.libs" | head -1)
            if [[ -n "$LIBS_DIR" ]]; then
                cp -r "$LIBS_DIR" "$STAGING/lib/"
                echo "    + loom_python_plugin.libs/"
            fi
        fi

        rm -rf "$UNPACK_TMP"
        found_any=1
    done

    if [[ $found_any -eq 0 ]]; then
        echo "WARNING: no wheels found for $platform — skipping zip" >&2
        rm -rf "$STAGING"
        return 0
    fi

    # Copy plugin source files
    for f in "${PLUGIN_FILES[@]}"; do
        if [[ -f "$REPO_ROOT/$f" ]]; then
            cp "$REPO_ROOT/$f" "$STAGING/"
            echo "  + $f"
        else
            echo "  WARNING: $f not found, skipping" >&2
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
    "loom_python_plugin-*-PYTAG-*manylinux*.whl" \
    "loom*.so" \
    "linux"

build_package \
    "windows" \
    "loom_python_plugin-*-PYTAG-*win_amd64*.whl" \
    "loom*.pyd" \
    "windows"

build_package \
    "macos-arm64" \
    "loom_python_plugin-*-PYTAG-*macosx*arm64*.whl" \
    "loom*.so" \
    "macos_arm64"

build_package \
    "macos-x86_64" \
    "loom_python_plugin-*-PYTAG-*macosx*x86_64*.whl" \
    "loom*.so" \
    "macos_x86_64"

echo ""
echo "Done."
