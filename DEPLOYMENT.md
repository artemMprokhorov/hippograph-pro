# Deployment Guide

Mehen Graph can run in four configurations. Choose the one that fits your setup.

---

## Scenario 1: Remote hosting (internet-accessible)

**Best for:** Teams, multi-user setups, access from anywhere.

### Deploy

```bash
git clone https://github.com/artemMprokhorov/Mehen-Graph.git
cd Mehen-Graph
cp .env.example .env
# Edit .env: set NEURAL_API_KEY to a strong random string

docker-compose up -d
```

### Expose via Nginx + SSL (recommended)

```nginx
# /etc/nginx/sites-enabled/mehen
server {
    listen 443 ssl;
    server_name memory.yourdomain.com;
    ssl_certificate     /etc/letsencrypt/live/memory.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/memory.yourdomain.com/privkey.pem;

    location /api/ {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
    }
    location /sse {
        proxy_pass http://localhost:5001;
        proxy_buffering off;
        proxy_cache off;
    }
}
```

```bash
certbot --nginx -d memory.yourdomain.com
nginx -s reload
```

### Alternative: Cloudflare Tunnel (no server port exposure)

```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared  # macOS
# or: curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared

cloudflared tunnel login
cloudflared tunnel create mehen
cloudflared tunnel route dns mehen memory.yourdomain.com
cloudflared tunnel run --url http://localhost:5001 mehen
```

### Access

| Interface | URL |
|-----------|-----|
| REST API | `https://memory.yourdomain.com/api/search` |
| MCP (Claude.ai) | `https://memory.yourdomain.com/sse?api_key=YOUR_KEY` |
| CLI | `MEHEN_API_URL=https://memory.yourdomain.com mehen search "query"` |

---

## Scenario 2: Local network, Docker

**Best for:** Home lab, NAS, Mac Studio, always-on local server.

### Deploy

```bash
git clone https://github.com/artemMprokhorov/Mehen-Graph.git
cd Mehen-Graph
cp .env.example .env
# Edit .env: set NEURAL_API_KEY

docker-compose up -d
```

### Access from any machine on your LAN

Find your server's local IP:
```bash
ipconfig getifaddr en0  # macOS
ip route get 1 | awk '{print $7}'  # Linux
```

| Interface | URL |
|-----------|-----|
| REST API | `http://192.168.0.X:5001/api/search` |
| MCP | `http://192.168.0.X:5001/sse?api_key=YOUR_KEY` |
| CLI | `MEHEN_API_URL=http://192.168.0.X:5001 mehen search "query"` |

### Claude Desktop config

```json
{
  "mcpServers": {
    "mehen": {
      "url": "http://192.168.0.X:5001/sse?api_key=YOUR_KEY"
    }
  }
}
```

No SSL needed on a trusted local network.

---

## Scenario 3: Local network, no Docker

**Best for:** Any machine with Python 3.10+, including Raspberry Pi, old laptops.

### Requirements

- Python 3.10+
- 4GB+ RAM (for BGE-M3 embedding model, ~1.5GB download on first run)
- SQLite (included with Python)

### Deploy

```bash
git clone https://github.com/artemMprokhorov/Mehen-Graph.git
cd Mehen-Graph

pip install -r requirements.txt
python3 -m spacy download xx_ent_wiki_sm
python3 -m spacy download en_core_web_sm

cp .env.example .env
# Edit .env: set NEURAL_API_KEY and DB_PATH

python3 src/server.py
```

### Auto-start on Linux (systemd)

```ini
# /etc/systemd/system/mehen.service
[Unit]
Description=Mehen Graph Memory Server
After=network.target

[Service]
WorkingDirectory=/opt/Mehen-Graph
ExecStart=python3 src/server.py
Restart=always
EnvironmentFile=/opt/Mehen-Graph/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable mehen
sudo systemctl start mehen
```

### Auto-start on macOS (launchd)

```xml
<!-- ~/Library/LaunchAgents/com.mehen.graph.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.mehen.graph</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/Users/you/Mehen-Graph/src/server.py</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>NEURAL_API_KEY</key><string>YOUR_KEY</string>
    <key>DB_PATH</key><string>/Users/you/mehen_memory.db</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.mehen.graph.plist
```

### Access

Same as Docker scenario — use `http://192.168.0.X:5000` (default port without Docker is 5000).

---

## Scenario 4: Everything on one machine

**Best for:** Personal use, laptop, developer setup.

### Deploy (Docker)

```bash
git clone https://github.com/artemMprokhorov/Mehen-Graph.git
cd Mehen-Graph
cp .env.example .env
docker-compose up -d
```

### Deploy (no Docker)

```bash
pip install -r requirements.txt
python3 -m spacy download xx_ent_wiki_sm
cp .env.example .env
python3 src/server.py &
```

### Access

| Interface | URL |
|-----------|-----|
| REST API | `http://localhost:5001/api/search` |
| MCP | `http://localhost:5001/sse?api_key=YOUR_KEY` |
| CLI | `mehen search "query"` |

### Claude Desktop config

```json
{
  "mcpServers": {
    "mehen": {
      "url": "http://localhost:5001/sse?api_key=YOUR_KEY"
    }
  }
}
```

---

## CLI (`mehen`) — all scenarios

### Install

```bash
# Option A: install script
curl -sSL https://raw.githubusercontent.com/artemMprokhorov/Mehen-Graph/main/install_mehen_cli.sh | bash

# Option B: manual
chmod +x mehen_cli.py
ln -sf $(pwd)/mehen_cli.py /usr/local/bin/mehen
```

### Configure

```bash
# Set in shell profile (~/.zshrc or ~/.bashrc)
export MEHEN_API_URL="http://192.168.0.X:5001"  # or https://memory.yourdomain.com
export MEHEN_API_KEY="your-api-key"
```

### Usage

```bash
mehen search "temporal retrieval results"
mehen search "what did we work on" --limit 5 --full
mehen add "Started H4 experiment" --category milestone --intensity 8
mehen stats
mehen sleep
mehen pcb
mehen graph 42
mehen repl                    # interactive mode
mehen search "query" --json   # machine-readable output for agents
```

### Agent integration (any language)

```bash
# Shell
result=$(mehen search "query" --json)

# Python
import subprocess, json
result = json.loads(subprocess.check_output(['mehen', 'search', 'query', '--json']))

# Node.js
const { execSync } = require('child_process');
const result = JSON.parse(execSync('mehen search "query" --json'));
```

---

## Interface comparison

| Interface | Best for | Protocol | Agent-native? |
|-----------|----------|----------|---------------|
| REST API | Any language, custom integrations | HTTP POST | Yes (with client code) |
| MCP | Claude-based agents (zero config) | SSE | Yes (plug and play) |
| CLI (`mehen`) | Shell agents, scripts, Claude Code | subprocess | Yes (`--json` flag) |

---

## Security checklist

- [ ] Set `NEURAL_API_KEY` to a strong random string (not the default)
- [ ] Never commit `.env` to git
- [ ] Use HTTPS for internet-facing deployments
- [ ] Restrict firewall to trusted IPs for local deployments
- [ ] Rotate API key if exposed

Generate a strong key:
```bash
python3 -c "import secrets; print('mehen_' + secrets.token_urlsafe(32))"
```