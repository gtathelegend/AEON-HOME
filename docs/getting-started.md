# Getting Started

## Prerequisites

| Component          | Requirement                                      |
|--------------------|--------------------------------------------------|
| Snapdragon X Elite | AI PC running Windows 11 or Linux                |
| Arduino            | Uno R4 WiFi or Nano 33 IoT                       |
| Python             | 3.11+                                            |
| Node.js            | 20+                                              |
| Arduino IDE        | 2.x or arduino-cli                               |
| QNN SDK (optional) | Qualcomm AI Engine Direct SDK for NPU inference  |

## 1. Clone and install

```bash
git clone https://github.com/your-org/aeon-home.git
cd aeon-home
```

## 2. Flash Arduino firmware

```bash
# Install required libraries
arduino-cli lib install "DHT sensor library" ArduinoJson

# Copy aeon_* libraries to your Arduino libraries folder
cp -r arduino/libraries/aeon_* ~/Arduino/libraries/

# Flash firmware (adjust port)
arduino-cli compile --fqbn arduino:avr:uno arduino/firmware/sentinel
arduino-cli upload  --port /dev/ttyUSB0 --fqbn arduino:avr:uno arduino/firmware/sentinel
```

## 3. Configure backend

```bash
cd backend
cp ../.env.example .env
# Edit .env — set AEON_SERIAL_PORT, AEON_DEVICE_ID, SARVAM_API_KEY, etc.

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 4. (Optional) Install QNN SDK

Download the SDK from https://developer.qualcomm.com/software/qualcomm-ai-engine-direct-sdk  
Then: `pip install <sdk>/python/qnn-*.whl`

Place compiled `.bin` model files in `backend/models/bin/`.  
Without the SDK the system falls back to ONNX Runtime on CPU.

## 5. Start backend

```bash
python -m aeon.main
# API:     http://localhost:8000/api/docs
# WS:      ws://localhost:8001
# Metrics: http://localhost:9090/metrics
```

## 6. Start frontend

```bash
# From workspace root
npm install
npm run dev
# Dashboard: http://localhost:3000
```

## 7. Verify

- Open http://localhost:3000 → Dashboard → Overview
- You should see live sensor data within a few seconds of the Arduino connecting
- The status bar should show "Local Network: Connected" and "Privacy: Enabled"

## Troubleshooting

| Problem                           | Solution                                              |
|-----------------------------------|-------------------------------------------------------|
| No serial data                    | Check AEON_SERIAL_PORT in .env; try `dmesg | grep tty` |
| QNN SDK not found                 | Normal on non-Snapdragon hardware; ONNX fallback used  |
| Dashboard shows stale data        | Check WebSocket connection in browser DevTools         |
| EEPROM recovery not working       | Ensure ArduinoJson and DHT libraries are installed     |
