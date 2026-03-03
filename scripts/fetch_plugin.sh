#!/usr/bin/env bash
# fetch_plugin.sh — Download the latest plugin zip from GitHub Releases
#
# No GitHub token required — release assets on public repos are publicly accessible.
#
# Requires: curl, jq
#   sudo apt install curl jq   (Debian/Ubuntu)
#   brew install curl jq       (macOS)
#
# Usage:
#   bash scripts/fetch_plugin.sh [options]
#
# Options:
#   --tag   Release tag to download  (default: latest)
#           Example: v1.2.3
#
# Output:
#   Plugin zip is saved to:  dist/loom_qgis_plugin.zip
#   Install it directly in QGIS via: Plugins > Manage and Install Plugins > Install from ZIP.

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
TAG="latest"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tag) TAG="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

OWNER="jordiMartinB"
REPO="loom-qgis-plugin"
ASSET_NAME="loom_qgis_plugin.zip"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
DIST_DIR="${REPO_ROOT}/dist"
OUT_FILE="${DIST_DIR}/${ASSET_NAME}"

BASE_API="https://api.github.com/repos/${OWNER}/${REPO}"

ACCEPT_HEADER="Accept: application/vnd.github+json"
API_VER_HEADER="X-GitHub-Api-Version: 2022-11-28"

gh_get() {
    curl -fsSL \
        -H "$ACCEPT_HEADER" \
        -H "$API_VER_HEADER" \
        "$1"
}

# ---------------------------------------------------------------------------
# Resolve the release
# ---------------------------------------------------------------------------
if [[ "$TAG" == "latest" ]]; then
    RELEASE_URL="${BASE_API}/releases/latest"
    echo "Fetching latest release..."
else
    RELEASE_URL="${BASE_API}/releases/tags/${TAG}"
    echo "Fetching release '${TAG}'..."
fi

RELEASE=$(gh_get "$RELEASE_URL")
RELEASE_TAG=$(echo  "$RELEASE" | jq -r '.tag_name')
RELEASE_NAME=$(echo "$RELEASE" | jq -r '.name')
RELEASE_DATE=$(echo "$RELEASE" | jq -r '.published_at')

echo "  Release: ${RELEASE_TAG}  '${RELEASE_NAME}'"
echo "  Published: ${RELEASE_DATE}"

# ---------------------------------------------------------------------------
# Find the plugin zip asset
# ---------------------------------------------------------------------------
DOWNLOAD_URL=$(echo "$RELEASE" | jq -r \
    --arg name "$ASSET_NAME" \
    '.assets[] | select(.name == $name) | .browser_download_url')

if [[ -z "$DOWNLOAD_URL" || "$DOWNLOAD_URL" == "null" ]]; then
    echo "" >&2
    echo "ERROR: Asset '${ASSET_NAME}' not found in release ${RELEASE_TAG}." >&2
    echo "Available assets:" >&2
    echo "$RELEASE" | jq -r '.assets[].name' | sed 's/^/  - /' >&2
    exit 1
fi

ASSET_SIZE=$(echo "$RELEASE" | jq -r \
    --arg name "$ASSET_NAME" \
    '.assets[] | select(.name == $name) | .size')
ASSET_KB=$(( ASSET_SIZE / 1024 ))
echo "  Asset: ${ASSET_NAME}  size=${ASSET_KB} KB"

# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------
mkdir -p "$DIST_DIR"

echo "Downloading to: ${OUT_FILE}"
curl -fsSL -L -o "$OUT_FILE" "$DOWNLOAD_URL"

echo ""
echo "Done: ${OUT_FILE}"
echo "Install in QGIS via: Plugins > Manage and Install Plugins > Install from ZIP"
