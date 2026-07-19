#!/usr/bin/env python3
"""
scripts/simulate_wifi_arduino.py

Simulates a live Arduino node sending telemetry data over WiFi to the local backend gateway.
It connects to the /ws/device WebSocket route and streams periodic updates.
"""

import asyncio
import json
import math
import random
import sys
import websockets
from datetime import datetime

BACKEND_WS_URL = "ws://localhost:8000/ws/device"

async def simulate_arduino():
    print(f"Connecting to ÆON Backend at {BACKEND_WS_URL}...")
    try:
        async with websockets.connect(BACKEND_WS_URL) as ws:
            print("Connected successfully! Starting telemetry stream...")
            
            seq = 1
            start_time = datetime.now()
            
            while True:
                # Time-based oscillation for temperature and humidity
                elapsed = (datetime.now() - start_time).total_seconds()
                temp = 22.5 + 2.0 * math.sin(elapsed / 120.0) + random.uniform(-0.1, 0.1)
                humidity = 48.0 + 5.0 * math.cos(elapsed / 180.0) + random.uniform(-0.5, 0.5)
                
                # Simulating human activity
                motion = random.random() < 0.35
                door = random.random() < 0.15
                
                # Prepare FeatureFrame JSON payload (matching FeatureFrame.from_json keys)
                sensor_payload = {
                    "typ": "sensor_update",
                    "temp": round(temp, 2),
                    "humidity": round(humidity, 1),
                    "motion": motion,
                    "door": door,
                    "mean_t": round(temp - 0.2, 2),
                    "var_t": 0.05,
                    "d_motion": 1.0 if motion else 0.0,
                    "ts": int(elapsed * 1000),
                    "seq": seq
                }
                
                print(f"Sending frame seq={seq} | Temp: {sensor_payload['temp']}°C | Hum: {sensor_payload['humidity']}% | Motion: {motion} | Door: {door}")
                await ws.send(json.dumps(sensor_payload))
                seq += 1
                
                # Every 5 frames, send a heartbeat
                if seq % 5 == 0:
                    heartbeat_payload = {
                        "typ": "heartbeat",
                        "device_id": "sentinel_01",
                        "seq": seq
                    }
                    print("Sending heartbeat...")
                    await ws.send(json.dumps(heartbeat_payload))
                
                # Every 8 frames, send some learning/status signals
                if seq % 8 == 0:
                    mem_payload = {
                        "typ": "memory_status",
                        "pct": random.randint(30, 45),
                        "seq": seq
                    }
                    print("Sending memory status updates...")
                    await ws.send(json.dumps(mem_payload))
                
                await asyncio.sleep(2.0)
                
    except ConnectionRefusedError:
        print("Error: Could not connect to the backend server. Make sure it is running on port 8000.")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(simulate_arduino())
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
        sys.exit(0)
