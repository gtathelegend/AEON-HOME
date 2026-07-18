#!/usr/bin/env bash
# scripts/setup_backend.sh — One-time backend environment setup.
#
# Usage: ./scripts/setup_backend.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"

echo "▶ ÆON Backend — setup"

# 1. Verify Python version
python3 --version | grep -qE "3\.(11|12|13)" || {
  echo "ERROR: Python 3.11+ required"
  exit 1
}

# 2. Create virtualenv
cd "$BACKEND_DIR"
if [ ! -d ".venv" ]; then
  echo "▶ Creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate

# 3. Install dependencies
echo "▶ Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Copy .env if needed
if [ ! -f "$REPO_ROOT/.env" ]; then
  echo "▶ Creating .env from .env.example..."
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  echo "  ⚠ Edit .env and set AEON_JWT_SECRET and AEON_SERIAL_PORT before starting."
fi

# 5. Create data directory
mkdir -p "$BACKEND_DIR/data"
mkdir -p "$BACKEND_DIR/models/bin"
mkdir -p "$BACKEND_DIR/models/src"

echo "✓ Backend setup complete."
echo ""
echo "Next steps:"
echo "  1. Edit .env — set AEON_SERIAL_PORT (e.g. /dev/ttyUSB0 or COM3)"
echo "  2. Generate JWT secret: python -c \"import secrets; print(secrets.token_hex(32))\""
echo "  3. cd backend && source .venv/bin/activate && python -m aeon.main"
