# HippoGraph Web Viewer

Interactive graph visualization for your Neural Memory system.

## 🚀 Quick Start

### Option 1: Local Network (Recommended)

Access via your local network - no internet exposure:

```
http://YOUR_LOCAL_IP:5002
```

**Configuration:**
- API Endpoint: `http://YOUR_LOCAL_IP:5001/sse2`
- API Key: Get from your `.env` file

### Option 2: Internet Access (ngrok)

Access from anywhere via HTTPS:

```
https://your-random-url.ngrok-free.app/viewer
```

**Configuration:**
- API Endpoint: `https://your-random-url.ngrok-free.app/sse2`
- API Key: Same as local

## 🔒 Security

**IMPORTANT:** The viewer requires API credentials that are NOT included in git.

### First Time Setup

1. Open the viewer in your browser
2. You'll see a configuration panel
3. Enter your connection details:
   - **API Endpoint URL**: Where your server is running
   - **API Key**: From your `.env` file

### Localhost vs Internet

**Localhost (YOUR_LOCAL_IP):**
- ✅ Secure by default
- ✅ Fast (no internet latency)
- ✅ Works offline
- ❌ Only accessible from local network

**Internet (ngrok):**
- ✅ Access from anywhere
- ✅ HTTPS encryption
- ❌ Requires ngrok setup
- ❌ Exposes server to internet

## 📝 Features

- **Interactive Graph** - Drag nodes, zoom, pan
- **Search** - Find notes by content
- **Filters** - Category, time range, link types
- **Timeline** - Watch your memory grow over time (with autoplay!)
- **Link Weights** - Visualize connection strength with colors
- **Click Links** - See weight and connection details

## 🛠️ Deployment

### Docker (Included)

The viewer is automatically served by the Docker container:

```bash
docker-compose up -d
```

Access at: `http://localhost:5002`

### Standalone

Copy `index.html` anywhere and open in browser. Configure connection on first load.

## 🔐 Privacy

- All data stays on YOUR server
- No third-party services
- Credentials stored in browser localStorage only
- Never committed to git

## 📚 Related Docs

- [GRAPH_VIEWER.md](../GRAPH_VIEWER.md) - Detailed security guide
- [README.md](../README.md) - Main project docs
- [SECURITY.md](../SECURITY.md) - Security best practices
