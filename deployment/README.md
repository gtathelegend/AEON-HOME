# Deployment

ÆON Home is designed to run **entirely on-device** (Snapdragon X Elite AI PC).
No cloud infrastructure is required for normal operation.

## Recommended setup

```
Snapdragon X Elite AI PC
  └── backend/       Python backend (systemd service)
  └── frontend/      PWA served by backend or nginx
  └── data/          SQLite memory store (local NVMe)

Arduino Sentinel
  └── Connected via USB to the AI PC

Mobile / Tablet
  └── Opens PWA via LAN browser (no app install needed)
```

## Systemd service (Linux)

```bash
# Copy the service file
sudo cp deployment/systemd/aeon-backend.service /etc/systemd/system/

# Edit WorkingDirectory and ExecStart paths
sudo systemctl daemon-reload
sudo systemctl enable aeon-backend
sudo systemctl start  aeon-backend
sudo journalctl -u aeon-backend -f
```

## Windows service

Use NSSM (Non-Sucking Service Manager) to wrap the Python process:

```powershell
nssm install AeonBackend "C:\path\to\.venv\Scripts\python.exe" "-m aeon.main"
nssm set AeonBackend AppDirectory "C:\path\to\backend"
nssm start AeonBackend
```

## Docker (optional, no NPU access)

```bash
docker compose -f deployment/docker/docker-compose.yml up
```

Note: Docker cannot access the Hexagon NPU. The ONNX CPU fallback will be
used. Suitable for development and CI only.

## Nginx reverse proxy (optional)

If you want to serve the PWA and API from a single port:

```nginx
server {
    listen 80;
    location /api/  { proxy_pass http://localhost:8000; }
    location /ws/   { proxy_pass http://localhost:8001; proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade"; }
    location /      { root /path/to/dist; try_files $uri /index.html; }
}
```
