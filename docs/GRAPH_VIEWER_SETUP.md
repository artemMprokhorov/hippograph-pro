# Graph Viewer - Setup & Configuration Guide

## 📊 Overview

HippoGraph includes an **interactive web-based graph viewer** for visualizing your knowledge graph. The viewer is automatically deployed via Docker and accessible through nginx.

**Key Features:**
- 🌐 Interactive D3.js visualization
- 🎨 Color-coded categories
- 📈 Link weight visualization
- ⏱️ Timeline playback with autoplay
- 🔍 Advanced filtering (category, time, link type)
- 🖱️ Click nodes and links for details
- 🔐 Secure configuration UI

---

## 🚀 Deployment Options

### Option 1: Localhost Only (Most Secure)

**Access:** Only from the same machine  
**Security:** Highest (no network exposure)  
**Setup:** Zero configuration needed

```bash
# Start server
docker-compose up -d

# Open in browser
http://localhost:5002
```

**Configuration:**
- API Endpoint: `http://localhost:5001/sse2`
- API Key: From your `.env` file

**Use Case:** Personal use, development, maximum security

---

### Option 2: Local Network (LAN)

**Access:** Any device on your network (192.168.x.x)  
**Security:** Network firewall protection  
**Setup:** Works out-of-the-box with Docker

```bash
# Start server
docker-compose up -d

# Find your local IP
ifconfig | grep "inet " | grep -v 127.0.0.1

# Open in browser from any device on LAN
http://YOUR_LOCAL_IP:5002  # Replace with your IP
```

**Configuration:**
- API Endpoint: `http://YOUR_LOCAL_IP:5001/sse2`
- API Key: From your `.env` file

**Use Case:** 
- Access from laptop, tablet, phone on same WiFi
- Team sharing on office network
- Multi-device workflow

---

### Option 3: Internet Access (HTTPS via ngrok)

**Access:** From anywhere with internet  
**Security:** HTTPS encrypted, API key required  
**Setup:** ngrok included in Docker

```bash
# Start server (ngrok starts automatically)
docker-compose up -d

# Get your ngrok URL
docker logs hippograph | grep "Internet:"
# Output: - Internet: https://your-domain.ngrok-free.app
```

**Configuration:**
- API Endpoint: `https://your-url.ngrok-free.app/sse2`
- API Key: From your `.env` file

**Viewer Access:**
- Via ngrok: `https://your-url.ngrok-free.app` (redirects to viewer)
- Direct: Access viewer via LAN, configure with ngrok API URL

**Use Case:**
- Remote access from coffee shop, travel
- Sharing with collaborators outside your network
- Claude.ai MCP + Web viewer from anywhere

**Security Notes:**
- ⚠️ Your graph is publicly accessible (with API key)
- ✅ HTTPS encryption protects credentials in transit
- ✅ API key authentication required
- 🔑 Use strong, unique API keys (32+ characters)
- 🔄 Rotate keys if exposed

---

## 🔐 Security Architecture

### Ports Exposed

| Port | Service | Access |
|------|---------|--------|
| 5001 | API Server (Flask) | API endpoints + MCP |
| 5002 | Web Viewer (nginx) | Static HTML viewer |

### Security Layers

**1. Network Level:**
- Docker internal network
- Host firewall (optional)
- Local network only (default)
- ngrok HTTPS tunnel (optional)

**2. Application Level:**
- API key authentication (NEURAL_API_KEY)
- CORS whitelisting
- Rate limiting (Flask)

**3. Web Viewer:**
- Content Security Policy (CSP)
- XSS protection (HTML escaping)
- Input validation (search, URLs)
- localStorage 7-day expiry
- No credentials in git

### CSP Policy

The viewer enforces strict Content Security Policy:

```
script-src:  self, unsafe-inline, https://d3js.org
style-src:   self, unsafe-inline
connect-src: localhost:5001, YOUR_LOCAL_IP:5001, *.ngrok-free.app
img-src:     self, data:
```

**What this means:**
- ✅ Only D3.js CDN allowed for scripts
- ✅ Only whitelisted API endpoints
- ❌ No unauthorized external connections
- ❌ No inline script injection

---

## ⚙️ Configuration Guide

### First-Time Setup

1. **Start Server:**
```bash
cd /path/to/hippograph
docker-compose up -d
```

2. **Get API Key:**
```bash
grep NEURAL_API_KEY .env
# Output: NEURAL_API_KEY=your_key_here
```

3. **Open Viewer:**
```bash
# Localhost
open http://localhost:5002

# LAN (replace with your IP)
open http://YOUR_LOCAL_IP:5002
```

4. **Configure Connection:**

In the viewer interface:
- **API Endpoint URL:** Choose based on deployment:
  - Localhost: `http://localhost:5001/sse2`
  - LAN: `http://YOUR_LOCAL_IP:5001/sse2`
  - Internet: `https://your-url.ngrok-free.app/sse2`
- **API Key:** Paste from `.env`
- Click "Connect and Load Graph"

5. **Save Credentials (Optional):**

When prompted, you can save credentials in browser localStorage:
- ✅ Saved locally in browser only
- ✅ 7-day automatic expiry
- ✅ Opt-in (you choose)
- ❌ Never sent to server
- ❌ Never in git

---

## 🔧 Advanced Configuration

### Custom ngrok Domain

If you have a paid ngrok account:

1. Edit `start.sh`:
```bash
ngrok http --url=your-custom-domain.ngrok.app 5000
```

2. Rebuild Docker:
```bash
docker-compose down
docker-compose up -d --build
```

### nginx Configuration

Viewer served by nginx (inside Docker). Configuration:
- **File:** `/etc/nginx/sites-available/hippograph`
- **Root:** `/var/www/html` (contains `index.html`)
- **Port:** 5002
- **Security headers:** X-Frame-Options, CSP, CORS

**To customize:**
1. Edit `nginx.conf` in repository
2. Rebuild: `docker-compose up -d --build`

### Disable Web Viewer

To run API only (no viewer):

1. Comment out in `docker-compose.yml`:
```yaml
# ports:
#   - "5002:5002"  # Disable viewer port
```

2. Restart:
```bash
docker-compose up -d
```

---

## 📱 Multi-Device Access

### Scenario: Access from Phone/Tablet

**Option A: LAN Access (Easy)**
1. Phone and server on same WiFi
2. Open: `http://YOUR_LOCAL_IP:5002`
3. Configure with LAN API endpoint
4. Save credentials for convenience

**Option B: Internet Access (Flexible)**
1. Use ngrok URL (works from anywhere)
2. Open: `https://your-url.ngrok-free.app`
3. Configure with ngrok API endpoint
4. Access from cellular data, any WiFi

### Scenario: Team Collaboration

**Small Team (Same Office):**
- Use LAN deployment (Option 2)
- Share IP address: `http://YOUR_LOCAL_IP:5002`
- Each person uses same API key (from `.env`)
- All view same knowledge graph

**Distributed Team:**
- Use ngrok deployment (Option 3)
- Share ngrok URL (HTTPS)
- Share API key securely (1Password, etc.)
- Consider separate graphs per team member

---

## 🛠️ Troubleshooting

### "Error: Failed to fetch"

**Possible Causes:**
1. Server not running
2. Wrong API URL
3. Wrong port (5001 vs 5002)
4. Network/firewall blocking

**Solution:**
```bash
# Check server status
docker ps | grep hippograph

# Check API health
curl http://localhost:5001/health
# Expected: {"status":"ok","version":"2.0.0"}

# Check viewer
curl http://localhost:5002
# Expected: HTML content

# Check logs
docker logs hippograph --tail 50
```

### "Error: Unauthorized"

**Cause:** Wrong or expired API key

**Solution:**
1. Get current key: `grep NEURAL_API_KEY .env`
2. Clear browser localStorage
3. Enter correct key in viewer config

### "Error: 'undefined' is not valid JSON"

**Cause:** CSP blocking cross-port requests (fixed in v2.1)

**Solution:**
1. Update to latest version: `git pull origin main`
2. Rebuild: `docker-compose down && docker-compose up -d --build`
3. Hard refresh browser: Ctrl+Shift+R

### Graph Loads but Shows No Nodes

**Cause:** Empty database

**Solution:**
1. Add some notes via MCP
2. Check stats: `curl http://localhost:5001/sse2?api_key=YOUR_KEY -d '{"method":"neural_stats"}'`
3. Reload viewer

### "CORS Policy" Errors

**Cause:** Browser blocking cross-origin requests

**Solution:**
1. Ensure API and viewer accessed via same method:
   - Both localhost, OR
   - Both LAN IP, OR  
   - Both HTTPS (ngrok)
2. Check CORS headers in nginx.conf
3. Rebuild if changed: `docker-compose up -d --build`

---

## 📚 Related Documentation

- [SECURITY_AUDIT.md](../SECURITY_AUDIT.md) - Security review and fixes
- [web/README.md](../web/README.md) - Web viewer specifics
- [MCP_CONNECTION.md](../MCP_CONNECTION.md) - API keys and MCP setup
- [README.md](../README.md) - General project overview

---

## 🔄 Updates & Version History

**v2.1 (Feb 4, 2026):**
- ✅ nginx deployment in Docker
- ✅ Security hardening (XSS, CSP, input validation)
- ✅ localStorage 7-day expiry
- ✅ Link weight visualization
- ✅ Timeline autoplay
- ✅ Click-to-inspect links
- ✅ Fixed CSP cross-port issues

**v2.0 (Feb 3, 2026):**
- ✅ Config UI (no hardcoded credentials)
- ✅ Category filters
- ✅ Time range filters
- ✅ Entity/semantic link toggle

**v1.0 (Jan 2026):**
- ✅ Initial D3.js visualization
- ✅ Basic node/edge rendering

---

## 🔒 Security Best Practices

### For Personal Use

✅ **DO:**
- Use localhost when possible
- Use strong API keys (32+ chars)
- Keep `.env` in `.gitignore`
- Enable localStorage expiry
- Rotate keys quarterly

❌ **DON'T:**
- Commit credentials to git
- Use weak API keys
- Expose to internet without HTTPS
- Share keys in plaintext

### For Team Use

✅ **DO:**
- Use HTTPS (ngrok or custom domain)
- Generate unique keys per team member
- Use password manager for key distribution
- Monitor access logs
- Implement IP whitelisting (nginx)
- Regular key rotation

❌ **DON'T:**
- Share keys via Slack/email
- Use same key for dev/prod
- Expose without authentication
- Ignore security updates

### For Public Demo

If creating public demo (conference, blog post):
- ✅ Use read-only API key (future feature)
- ✅ Limit data to non-sensitive demo content
- ✅ Monitor access closely
- ✅ Delete demo deployment after use
- ❌ Never expose real personal/business data

---

**Last Updated:** February 4, 2026  
**Maintainer:** Artem (with Claude)  
**Status:** Production Ready
