# Smart Home API - Quick Start Guide

## Setup

### 1. Install Dependencies

On your Raspberry Pi, navigate to the project directory and install dependencies:

```bash
cd ~/zigbeemcp  # or wherever you cloned zigbeemcp
uv sync
```

This will install FastAPI, uvicorn, and all other dependencies.

### 2. Configure API Keys

Create or update your `.env` file with API keys:

```bash
cp .env.example .env
nano .env
```

**IMPORTANT:** Set a strong API key:

```bash
API_KEYS=your-very-secret-api-key-here
```

You can generate a secure key with:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Start the Server

**Development mode (foreground):**
```bash
uv run smart-server
```

The server will start on `http://0.0.0.0:8000`

**Production mode (systemd service):**
```bash
# Copy and enable the service
sudo cp systemd/smartserver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable smartserver
sudo systemctl start smartserver

# Check status
sudo systemctl status smartserver
sudo journalctl -u smartserver -f

# Restart after code changes
sudo systemctl restart smartserver
```

### 4. Test the API

**View API documentation:**

Open your browser and navigate to:
- `http://<raspberry-pi-ip>:8000/docs` - Interactive Swagger UI
- `http://<raspberry-pi-ip>:8000/redoc` - Alternative documentation

**Test with curl:**
```bash
# Health check (no auth)
curl http://localhost:8000/health

# List devices (requires API key)
curl -H "X-API-Key: your-very-secret-api-key-here" \
  http://localhost:8000/api/devices

# Get device state
curl -H "X-API-Key: your-very-secret-api-key-here" \
  http://localhost:8000/api/devices/Bedroom1

# Toggle a light
curl -X POST http://localhost:8000/api/devices/Bedroom1/set \
  -H "X-API-Key: your-very-secret-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"state": "TOGGLE"}'
```

**Test with the provided script:**
```bash
# Full test suite
uv run scripts/test_api.py --api-key your-very-secret-api-key-here --full

# Toggle a specific device
uv run scripts/test_api.py --api-key your-very-secret-api-key-here \
  --device Bedroom1 --toggle
```

## Common Operations

### Control a Device

```bash
# Turn on with full brightness
curl -X POST http://localhost:8000/api/devices/Bedroom1/set \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"state": "ON", "brightness": 254}'

# Set warm color temperature
curl -X POST http://localhost:8000/api/devices/Bedroom1/set \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"color_temp": 400}'

# Dim with 2-second transition
curl -X POST http://localhost:8000/api/devices/Bedroom1/set \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"brightness": 50, "transition": 2.0}'
```

### Query Event History

```bash
# Get last 50 events
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:8000/api/events?limit=50"

# Get events for specific device
curl -H "X-API-Key: YOUR_KEY" \
  "http://localhost:8000/api/events?device=Bedroom1&limit=20"
```

### Bridge Operations

```bash
# Check bridge health
curl -H "X-API-Key: YOUR_KEY" \
  http://localhost:8000/api/bridge/health

# Enable device pairing for 60 seconds
curl -X POST http://localhost:8000/api/bridge/permit_join \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"time": 60}'
```

## Making It Accessible from the Internet

### Option 1: Tailscale (Recommended for Personal Use)

1. Install Tailscale on your Raspberry Pi:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```

2. Install Tailscale on your devices (laptop, phone, etc.)

3. Access your API from anywhere via Tailscale IP:
   ```bash
   curl -H "X-API-Key: YOUR_KEY" \
     http://100.x.x.x:8000/api/devices
   ```

### Option 2: Cloudflare Tunnel (For Public Access)

1. Set up Cloudflare Tunnel on your Pi
2. Configure tunnel to forward to `localhost:8000`
3. Access via: `https://smarthome.yourdomain.com/api/devices`

### Option 3: Port Forwarding + Dynamic DNS

1. Forward port 8000 on your router to the Raspberry Pi
2. Set up Dynamic DNS (e.g., DuckDNS)
3. **Important:** Consider setting up HTTPS with Let's Encrypt

## Troubleshooting

### Server won't start

**Check API_KEYS is set:**
```bash
grep API_KEYS .env
```

If missing, add it to `.env`:
```bash
echo "API_KEYS=your-secret-key-here" >> .env
```

**Check MQTT is running:**
```bash
sudo systemctl status mosquitto
```

**View server logs:**
```bash
# If running via systemd
sudo journalctl -u smartserver -f

# If running manually, check terminal output
```

### Authentication errors

Make sure you're sending the API key in the header:
```bash
curl -H "X-API-Key: your-api-key-here" http://localhost:8000/api/devices
```

### Device commands timeout

- Check that Zigbee2MQTT is running
- Verify device is online: `curl -H "X-API-Key: KEY" http://localhost:8000/api/devices`
- Check MQTT broker: `sudo systemctl status mosquitto`
- Increase timeout in `.env`: `API_DEVICE_STATE_TIMEOUT=10.0`

## Next Steps

- **Build a Dashboard:** Use the API to create a web or mobile dashboard
- **Voice Control:** Integrate with voice assistants via the API
- **Automation:** Create scripts or services that call the API based on schedules or triggers
- **MCP Integration:** Wrap the API with fastMCP for AI agent control (future enhancement)

For full documentation, see [CLAUDE.md](CLAUDE.md)
