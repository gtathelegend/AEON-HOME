#!/usr/bin/env python3
"""
scripts/simulate_serial_arduino.py

Simulates an Arduino UNO Q sending telemetry data over USB Serial port (COM10).
Outputs serial JSON lines continuously at 115200 baud.
"""

import sys
import time
import math
import random
import json
import serial

DEFAULT_PORT = "COM10"
DEFAULT_BAUD = 115200

def simulate_serial_arduino(port=DEFAULT_PORT, baud=DEFAULT_BAUD):
    print(f"Opening Serial Port {port} @ {baud} baud...")
    try:
        ser = serial.Serial(port, baud, timeout=1)
        print(f"Serial port {port} opened successfully! Streaming telemetry...")
    except serial.SerialException as e:
        print(f"Error opening serial port {port}: {e}")
        print("Note: In Windows, COM10 must exist (e.g., via com0com or physical device).")
        sys.exit(1)

    seq = 1
    start_t = time.time()

    try:
        while True:
            elapsed = time.time() - start_t
            temp = 22.5 + 2.0 * math.sin(elapsed / 120.0) + random.uniform(-0.1, 0.1)
            humidity = 48.0 + 5.0 * math.cos(elapsed / 180.0) + random.uniform(-0.5, 0.5)
            motion = random.random() < 0.35
            door = random.random() < 0.15

            payload = {
                "protocol_version": 1,
                "typ": "sensor_update",
                "device_id": "sentinel_01",
                "sequence": seq,
                "temp": round(temp, 2),
                "humidity": round(humidity, 1),
                "motion": 1 if motion else 0,
                "door": 1 if door else 0,
                "model_v": 100,
                "profile_v": 1,
                "pref_temp": 22.0,
                "activity": "Active" if motion else "Idle",
                "policy": "automation_policy" if motion else "background_policy",
                "confidence": 0.95 if motion else 0.80,
            }

            line = json.dumps(payload) + "\n"
            ser.write(line.encode("utf-8"))
            print(f"[{port}] Sent seq={seq} | Temp: {payload['temp']}C | Motion: {motion}")
            seq += 1

            if ser.in_waiting > 0:
                inbound = ser.readline().decode("utf-8", errors="ignore").strip()
                if inbound:
                    print(f"[{port}] Received command from backend: {inbound}")

            time.sleep(2.0)
    except KeyboardInterrupt:
        print("\nSerial simulation stopped.")
    finally:
        ser.close()

if __name__ == "__main__":
    port_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PORT
    simulate_serial_arduino(port=port_arg)
