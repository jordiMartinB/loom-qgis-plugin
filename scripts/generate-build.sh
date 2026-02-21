#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOOM_SRC="$REPO_ROOT/src/loom"
BUILD_DIR="$LOOM_SRC/build"
TOOLCHAIN_FILE="$LOOM_SRC/cmake/mingw-toolchain.cmake"
INSTALL_DIR="$REPO_ROOT/build"
JOBS="${JOBS:-$(nproc)}"

# simple logging: set LOG_LEVEL=ERROR|WARN|INFO|DEBUG|TRACE (default INFO)
LOG_LEVEL="${LOG_LEVEL:-INFO}"
log_level_value() {
  case "${1^^}" in
    ERROR) echo 0 ;;
    WARN)  echo 1 ;;
    INFO)  echo 2 ;;
    DEBUG) echo 3 ;;
    TRACE) echo 4 ;;
    *)     echo 2 ;;
  esac
}
LOG_LEVEL_VAL=$(log_level_value "$LOG_LEVEL")
log() {
  local lvl="$1"; shift
  local lvl_val
  lvl_val=$(log_level_value "$lvl")
  if [ "$lvl_val" -le "$LOG_LEVEL_VAL" ]; then
    printf "%s [%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S.%3N')" "$lvl" "$*" >&2
  fi
}

# parse flags
CLEAN=0
CLEAN_ONLY=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --clean|-c)
      CLEAN=1
      shift
      ;;
    --clean-only)
      CLEAN_ONLY=1
      shift
      ;;
    --help|-h)
      printf "Usage: %s [--clean|-c] [--clean-only]\n" "$0"
      exit 0
      ;;
    *)
      printf "Unknown option: %s\n" "$1" >&2
      exit 2
      ;;
  esac
done

if [ "$CLEAN" -eq 1 ] || [ "$CLEAN_ONLY" -eq 1 ]; then
  log INFO "Cleaning build directories: $BUILD_DIR and $INSTALL_DIR"
  rm -rf "$BUILD_DIR" "$INSTALL_DIR"
  if [ "$CLEAN_ONLY" -eq 1 ]; then
    log INFO "Clean-only requested, exiting."
    exit 0
  fi
fi

if ! command -v cmake >/dev/null 2>&1; then
  log ERROR "cmake is required but not found"
  exit 1
fi

if [ ! -f "$TOOLCHAIN_FILE" ]; then
  log ERROR "Toolchain file not found: $TOOLCHAIN_FILE"
  exit 1
fi

mkdir -p "$BUILD_DIR"
mkdir -p "$INSTALL_DIR"

log INFO "Configuring build in: $BUILD_DIR"
cmake -S "$LOOM_SRC" -B "$BUILD_DIR" \
  -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN_FILE" \
  -DCMAKE_BUILD_TYPE=Release

log INFO "Building (jobs=$JOBS)"
cmake --build "$BUILD_DIR" -- -j"$JOBS"

log INFO "Collecting build artifacts to: $INSTALL_DIR"
# copy common windows/linux artifacts to top-level build dir (flatten)
find "$BUILD_DIR" -type f \( -iname '*.exe' -o -iname '*.dll' -o -iname 'lib*.a' -o -iname '*.lib' -o -iname '*.so' \) -print0 \
  | xargs -0 -I{} cp -v {} "$INSTALL_DIR/"

# Move .exe files from src/loom/build to build/
log INFO "Moving .exe files to: $INSTALL_DIR"
find "$BUILD_DIR" -type f -iname '*.exe' -exec mv -v {} "$INSTALL_DIR/" \;

log INFO "Done."
