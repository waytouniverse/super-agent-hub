#!/bin/bash
# Build the Python backend binary with PyInstaller
# Output: pyinstaller-dist/agent-hub-backend
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "==> Activating virtual environment..."
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
fi

echo "==> Installing PyInstaller..."
python3 -m pip install pyinstaller --quiet

echo "==> Building frontend..."
cd frontend && npm run build && cd ..

echo "==> Cleaning previous build..."
rm -rf build dist pyinstaller-dist

echo "==> Building backend binary with PyInstaller..."
python3 -m PyInstaller \
    --onefile \
    --name agent-hub-backend \
    --add-data "frontend/dist:frontend/dist" \
    --hidden-import uvicorn \
    --hidden-import uvicorn.logging \
    --hidden-import uvicorn.loops \
    --hidden-import uvicorn.loops.auto \
    --hidden-import uvicorn.protocols \
    --hidden-import uvicorn.protocols.http \
    --hidden-import uvicorn.protocols.http.auto \
    --hidden-import uvicorn.protocols.websockets \
    --hidden-import uvicorn.protocols.websockets.auto \
    --hidden-import uvicorn.lifespan \
    --hidden-import uvicorn.lifespan.on \
    --hidden-import fastapi \
    --hidden-import websockets \
    --hidden-import websockets.legacy \
    --hidden-import websockets.legacy.http \
    --hidden-import websockets.legacy.server \
    --hidden-import asyncio \
    --collect-submodules agent_hub \
    desktop_entry.py

echo "==> Copying output..."
mkdir -p pyinstaller-dist
cp dist/agent-hub-backend pyinstaller-dist/agent-hub-backend
chmod +x pyinstaller-dist/agent-hub-backend

echo "==> Backend binary size:"
ls -lh pyinstaller-dist/agent-hub-backend

echo "==> Backend build complete!"
