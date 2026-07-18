#!/usr/bin/env bash
# scripts/flash_arduino.sh — Compile and flash the ÆON Sentinel firmware.
#
# Usage:
#   ./scripts/flash_arduino.sh [PORT] [FQBN]
#
# Defaults:
#   PORT  = /dev/ttyUSB0
#   FQBN  = arduino:avr:uno
#
# Requires: arduino-cli on PATH

set -euo pipefail

PORT="${1:-/dev/ttyUSB0}"
FQBN="${2:-arduino:avr:uno}"
SKETCH="firmware/firmware/sentinel"
LIBS_SRC="firmware/libraries"
ARDUINO_LIB_DIR="${HOME}/Arduino/libraries"

echo "▶ ÆON Sentinel — flash"
echo "  Port : $PORT"
echo "  Board: $FQBN"

# 1. Install third-party libraries
echo "▶ Installing dependencies..."
arduino-cli lib install "DHT sensor library" "ArduinoJson"

# 2. Copy ÆON libraries into Arduino library path
echo "▶ Copying ÆON libraries..."
for lib in "$LIBS_SRC"/aeon_*; do
  dest="$ARDUINO_LIB_DIR/$(basename "$lib")"
  rm -rf "$dest"
  cp -r "$lib" "$dest"
  echo "   ✓ $(basename "$lib")"
done

# 3. Compile
echo "▶ Compiling..."
arduino-cli compile --fqbn "$FQBN" "$SKETCH"

# 4. Upload
echo "▶ Flashing to $PORT..."
arduino-cli upload --port "$PORT" --fqbn "$FQBN" "$SKETCH"

echo "✓ Done. Arduino Sentinel is running."
