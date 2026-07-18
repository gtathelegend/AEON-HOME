# ÆON Home — PWA Local Network Setup

This document explains how to connect the ÆON mobile PWA to the Snapdragon X Elite
edge backend running on your local network.

---

## Architecture

```
Phone (PWA, HTTPS or HTTP)
        │
        │  WebSocket  ws://192.168.x.x:8001
        │  REST HTTP  http://192.168.x.x:8000
        ▼
Snapdragon X Elite (backend, Python)
        │
        │  USB Serial (115200 baud)
        ▼
Arduino Sentinel (firmware)
```

The backend runs entirely on the Snapdragon X Elite machine.
No cloud relay is involved. The phone connects directly over LAN.

---

## Step 1 — Start the backend on Snapdragon

```bash
cd backend
pip install -r requirements.txt
python -m aeon.main
```

The backend listens on:
- `0.0.0.0:8000` — REST API
- `0.0.0.0:8001` — WebSocket bus

Both ports must be reachable from the phone over LAN.

---

## Step 2 — Find the Snapdragon machine's LAN IP

On Windows (Snapdragon):
```powershell
ipconfig | findstr "IPv4"
```

On Linux/macOS:
```bash
hostname -I
```

Example result: `192.168.1.42`

---

## Step 3 — Configure the frontend

Set the backend URL in `frontend/.env.local`:

```
VITE_API_BASE_URL=http://192.168.1.42:8000
VITE_WS_URL=ws://192.168.1.42:8001
```

Then build and serve:

```bash
cd frontend
npm run build
npm run preview -- --host 0.0.0.0 --port 5173
```

Access from phone: `http://192.168.1.42:5173`

---

## Step 4 — Open firewall ports (Windows)

If the phone cannot connect, allow the ports through Windows Firewall:

```powershell
New-NetFirewallRule -DisplayName "AEON API" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
New-NetFirewallRule -DisplayName "AEON WS"  -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow
New-NetFirewallRule -DisplayName "AEON PWA" -Direction Inbound -Protocol TCP -LocalPort 5173 -Action Allow
```

---

## Step 5 — Verify connectivity

From the phone browser, open:
```
http://192.168.1.42:8000/api/v1/health
```

Expected response:
```json
{"status": "ok", "version": "1.0.0"}
```

If this works, the PWA dashboard will connect automatically.

---

## HTTPS / Mixed Content

If the frontend is served over **HTTPS** (e.g. deployed to Vercel/Netlify for demo),
browsers will block connections to plain `ws://` or `http://` LAN endpoints due to
mixed-content restrictions.

**Solutions:**

### Option A — Run everything over HTTP (recommended for hackathon LAN)
Serve the frontend locally over HTTP as described above. No mixed-content issue.

### Option B — Use a self-signed certificate
1. Generate a cert for the Snapdragon machine's IP:
   ```bash
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem \
     -days 30 -nodes -subj "/CN=192.168.1.42"
   ```
2. Run uvicorn with SSL:
   ```bash
   uvicorn aeon.api.app:app --ssl-keyfile key.pem --ssl-certfile cert.pem \
     --host 0.0.0.0 --port 8000
   ```
3. Update env vars to use `https://` and `wss://`.
4. Trust the cert on the phone (visit `https://192.168.1.42:8000` and accept the warning).

---

## PWA Connection Status

The dashboard displays one of:
- **Edge Connected** — WebSocket open, receiving real telemetry
- **Connecting...** — Auto-discovery in progress
- **Disconnected** — WebSocket closed; all sensor values show "Arduino disconnected" or "Waiting for sensor..."

The frontend **never silently falls back to fake data**.
If the backend is unreachable, all metric cards show honest disconnected states.

---

## Environment Variable Reference

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | REST API base URL |
| `VITE_WS_URL` | auto-derived from origin | WebSocket URL |
| `VITE_DEMO_MODE` | `false` | Enable simulated data (dev only) |
| `AEON_SERIAL_PORT` | `/dev/ttyUSB0` | Arduino serial port |
| `AEON_API_PORT` | `8000` | Backend REST port (WS = port+1) |
| `SARVAM_API_KEY` | `` | Sarvam AI API key for voice STT/TTS |
| `SARVAM_OFFLINE` | `true` | Skip Sarvam when key not set |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Phone shows "Disconnected" | Check firewall; verify IP in env vars |
| Serial shows "Arduino disconnected" | Check `AEON_SERIAL_PORT`; verify Arduino is plugged in via USB |
| Voice returns "API key not configured" | Set `SARVAM_API_KEY` in `backend/.env` |
| WS connects but no sensor data | Arduino firmware not flashed; see `arduino/README.md` |
| Mixed content error in browser | Use HTTP for LAN demo; see HTTPS section above |
