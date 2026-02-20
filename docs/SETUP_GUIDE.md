# Setup Guide

Complete installation and configuration guide for Neural Memory Graph.

---

## Prerequisites

- **Docker** and **Docker Compose** installed
- **4GB+ RAM** (embedding model requires ~2GB)
- **3GB+ disk space** (Docker image + models)
- For remote access: **Reverse proxy solution** (ngrok, Cloudflare Tunnel, or custom)

---

## Quick Start (Local Only)

### 1. Clone Repository

```bash
git clone https://github.com/artemMprokhorov/hippograph-pro.git
cd neural-memory-graph
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set a strong API key:
```bash
NEURAL_API_KEY=your_very_secure_random_key_here_32plus_chars
```

### 3. Start Server

```bash
docker-compose up -d
```

The server will:
- Download embedding models (~2GB, first run only)
- Download spaCy model for entity extraction
- Initialize SQLite database
- Start Flask server on `http://localhost:5000`

### 4. Verify Installation

```bash
curl http://localhost:5000/health
# Expected: {"status": "ok", "version": "2.0.0"}
```

---

## Remote Access Setup

To connect from Claude.ai or use from different machines, you need a public HTTPS URL. Choose one of these options:

### Option A: ngrok (Easiest, for testing)

**Pros:** Quick setup, free tier available  
**Cons:** URL changes on restart (free tier), monthly bandwidth limits

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/download

# Authenticate (get token from https://dashboard.ngrok.com)
ngrok config add-authtoken YOUR_NGROK_TOKEN

# Create tunnel
ngrok http 5000

# Copy the https://xxx.ngrok-free.app URL
```

### Option B: Cloudflare Tunnel (Recommended for persistent use)

**Pros:** Free, persistent URL, no bandwidth limits  
**Cons:** Requires domain name (can use Cloudflare's free subdomain)

```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared  # macOS
# or download from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

# Login and setup
cloudflared tunnel login
cloudflared tunnel create neural-memory
cloudflared tunnel route dns neural-memory memory.yourdomain.com

# Create config: ~/.cloudflared/config.yml
tunnel: YOUR_TUNNEL_ID
credentials-file: /path/to/credentials.json

ingress:
  - hostname: memory.yourdomain.com
    service: http://localhost:5000
  - service: http_status:404

# Run tunnel
cloudflared tunnel run neural-memory
```

### Option C: Custom Reverse Proxy (Advanced)

If you have a server with public IP:

**Nginx:**
```nginx
server {
    listen 443 ssl;
    server_name memory.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Caddy:**
```
memory.yourdomain.com {
    reverse_proxy localhost:5000
}
```

---

## Connect to Claude.ai

Once you have a public HTTPS URL:

1. Go to **Claude.ai → Settings → Integrations**
2. Click **Add Remote MCP Server**
3. Enter URL: `https://your-domain.com/sse?api_key=YOUR_API_KEY`
4. Save and test

Test the connection:
```
You: What tools do you have available?
Claude: I have access to: search_memory, add_note, update_note, ...
```

---

## Configuration

### Entity Extraction Modes

Edit `.env` to choose extraction method:

```bash
# Fast, no dependencies (default if spaCy fails)
ENTITY_EXTRACTOR=regex

# Better accuracy, requires spaCy model (recommended)
ENTITY_EXTRACTOR=spacy
```

### Spreading Activation Parameters

```bash
# Number of hops through the graph (1-5)
ACTIVATION_ITERATIONS=3

# Decay per hop (0.5-0.9, lower = faster decay)
ACTIVATION_DECAY=0.7

# Minimum similarity for semantic links (0.3-0.8)
SIMILARITY_THRESHOLD=0.5

# Blend scoring: balance between semantic similarity and graph activation
# 1.0 = pure semantic, 0.0 = pure spreading activation
BLEND_ALPHA=0.7
```

### Temporal Decay

```bash
# Half-life in days (after this, activation halves)
# 30 = month-old notes have 0.5x weight
# 90 = quarter-old notes have 0.5x weight
HALF_LIFE_DAYS=30
```

---

## Database Management

### Backup

```bash
./scripts/backup.sh
# Creates timestamped backup in ./backups/
```

### Restore

```bash
./scripts/restore.sh backups/memory_backup_20260126.db
```

### Manual Backup

```bash
docker exec neural-memory-graph sqlite3 /app/data/memory.db ".backup /app/data/backup.db"
docker cp neural-memory-graph:/app/data/backup.db ./my-backup.db
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs neural-memory-graph

# Common issues:
# - Port 5000 already in use → change port in docker-compose.yml
# - Permission denied → check ./data directory permissions
# - Out of memory → embedding model needs ~2GB RAM
```

### spaCy model download fails

```bash
# Download manually
docker exec neural-memory-graph python -m spacy download en_core_web_sm

# Or switch to regex mode in .env
ENTITY_EXTRACTOR=regex
```

### API returns 401 Unauthorized

- Check API key in URL matches `.env` file
- Special characters in key may need URL encoding
- Try using header instead: `-H "Authorization: Bearer YOUR_KEY"`

### MCP connection fails in Claude.ai

- Verify public URL is accessible: `curl https://your-url/health`
- Check firewall isn't blocking incoming connections
- Ensure using HTTPS (Claude.ai requires it)
- Verify API key is included in URL

---

## Security Hardening

### Production Deployment

1. **Strong API Key**
   ```bash
   # Generate secure key (32+ chars)
   openssl rand -base64 32
   ```

2. **HTTPS Only**
   - Never expose HTTP publicly
   - Use Let's Encrypt for free SSL certificates

3. **Firewall Rules**
   ```bash
   # Only allow connections from specific IPs
   ufw allow from YOUR_IP to any port 5000
   ```

4. **Rate Limiting**
   - Use reverse proxy (Nginx, Caddy) with rate limiting
   - Prevent brute-force API key attacks

5. **Regular Backups**
   ```bash
   # Add to crontab
   0 2 * * * /path/to/neural-memory-graph/scripts/backup.sh
   ```

---

## Monitoring

### Check Memory Usage

```bash
docker stats neural-memory-graph
```

### View Logs

```bash
# Real-time logs
docker logs -f neural-memory-graph

# Last 100 lines
docker logs --tail 100 neural-memory-graph
```

### Database Statistics

```bash
# Via MCP (if connected to Claude)
Claude: "Show me neural memory statistics"

# Via curl
curl "http://localhost:5000/sse?api_key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"neural_stats","arguments":{}}}'
```

---

## Updating

```bash
# Pull latest changes
git pull origin main

# Rebuild container
docker-compose down
docker-compose up -d --build

# Database migrations are automatic
```

---

## Uninstall

```bash
# Stop and remove container
docker-compose down

# Remove data (WARNING: deletes all notes!)
rm -rf ./data

# Remove Docker image
docker rmi neural-memory-graph
```
