#!/bin/bash
# One-stop build: frontend + PyInstaller backend + Tauri desktop app
# Output: src-tauri/target/release/bundle/dmg/Agent Hub_*.dmg
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "========================================="
echo " Agent Hub Desktop App Build"
echo "========================================="

echo ""
echo "[1/3] Building Python backend binary..."
bash scripts/build-backend.sh

echo ""
echo "[2/3] Verifying backend binary..."
if [ ! -f pyinstaller-dist/agent-hub-backend ]; then
    echo "ERROR: Backend binary not found!"
    exit 1
fi

echo ""
echo "[3/3] Building Tauri desktop app..."
cargo tauri build --bundles dmg 2>&1 | tail -20

echo ""
echo "========================================="
echo " Build complete!"
echo ""

DMG_PATH=$(ls src-tauri/target/release/bundle/dmg/Agent\ Hub_*.dmg 2>/dev/null | head -1)
if [ -n "$DMG_PATH" ]; then
    echo "DMG: $DMG_PATH"
    echo ""

    # Copy to WUDIAgent directory
    DEST="/Users/yeyuanxun/Downloads/我的工作台/程序/wudicode/WUDIAgent"
    echo "Copying to $DEST..."
    cp "$DMG_PATH" "$DEST/"
    echo "Done: $DEST/$(basename "$DMG_PATH")"
else
    echo "WARNING: DMG not found. Check Tauri build output above."
fi
