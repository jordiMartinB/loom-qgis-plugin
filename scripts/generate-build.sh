#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOOM_SRC="$REPO_ROOT/src/loom"
BUILD_DIR="$LOOM_SRC/build"
TOOLCHAIN_FILE="$LOOM_SRC/cmake/mingw-toolchain.cmake"
INSTALL_DIR="$REPO_ROOT/build"
JOBS="${JOBS:-$(nproc)}"

if ! command -v cmake >/dev/null 2>&1; then
  echo "cmake is required but not found" >&2
  exit 1
fi

if [ ! -f "$TOOLCHAIN_FILE" ]; then
  echo "Toolchain file not found: $TOOLCHAIN_FILE" >&2
  exit 1
fi

mkdir -p "$BUILD_DIR"
mkdir -p "$INSTALL_DIR"

echo "Configuring build in: $BUILD_DIR"
cmake -S "$LOOM_SRC" -B "$BUILD_DIR" \
  -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN_FILE" \
  -DCMAKE_BUILD_TYPE=Release

echo "Building (jobs=$JOBS)"
cmake --build "$BUILD_DIR" -- -j"$JOBS"

echo "Collecting build artifacts to: $INSTALL_DIR"
# copy common windows/linux artifacts to top-level build dir (flatten)
find "$BUILD_DIR" -type f \( -iname '*.exe' -o -iname '*.dll' -o -iname 'lib*.a' -o -iname '*.lib' -o -iname '*.so' \) -print0 \
  | xargs -0 -I{} cp -v {} "$INSTALL_DIR/"

echo "Done."
```// filepath: /home/jmb/Projects/loom-qgis-plugin/scripts/generate-build.sh
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOOM_SRC="$REPO_ROOT/src/loom"
BUILD_DIR="$LOOM_SRC/build"
TOOLCHAIN_FILE="$LOOM_SRC/cmake/mingw-toolchain.cmake"
INSTALL_DIR="$REPO_ROOT/build"
JOBS="${JOBS:-$(nproc)}"

if ! command -v cmake >/dev/null 2>&1; then
  echo "cmake is required but not found" >&2
  exit 1
fi

if [ ! -f "$TOOLCHAIN_FILE" ]; then
  echo "Toolchain file not found: $TOOLCHAIN_FILE" >&2
  exit 1
fi

mkdir -p "$BUILD_DIR"
mkdir -p "$INSTALL_DIR"

echo "Configuring build in: $BUILD_DIR"
cmake -S "$LOOM_SRC" -B "$BUILD_DIR" \
  -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN_FILE" \
  -DCMAKE_BUILD_TYPE=Release

echo "Building (jobs=$JOBS)"
cmake --build "$BUILD_DIR" -- -j"$JOBS"

echo "Collecting build artifacts to: $INSTALL_DIR"
# copy common windows/linux artifacts to top-level build dir (flatten)
find "$BUILD_DIR" -type f \( -iname '*.exe' -o -iname '*.dll' -o -iname 'lib*.a' -o -iname '*.lib' -o -iname '*.so' \) -print0 \
  | xargs -0 -I{} cp -v {} "$INSTALL_DIR/"

echo "Done."