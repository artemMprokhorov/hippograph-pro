# MCP Integration Guide

How to connect Neural Memory Graph to Claude.ai and other MCP clients.

## What is MCP?

Model Context Protocol (MCP) is Anthropic's standard for connecting AI assistants to external tools and data sources. Neural Memory Graph implements MCP via Server-Sent Events (SSE).

## Prerequisites

1. **Running server** - See [Setup Guide](SETUP_GUIDE.md) to start the server
2. **Public HTTPS URL** - Required for Claude.ai (local HTTP won't work)
3. **API Key** - Set in your `.env` file

## Getting a Public URL

Claude.ai requires HTTPS. Choose one option:

### Option 1: ngrok (Quick Testing)
```bash
ngrok http 5000
# Copy the https://xxx.ngrok-free.app URL
```

### Option 2: Cloudflare Tunnel (Recommended)
```bash
cloudflared tunnel --url http://localhost:5000
# Or setup persistent tunnel - see SETUP_GUIDE.md
```

### Option 3: Custom Domain
Use your own reverse proxy (Nginx, Caddy) with SSL certificate.

See [Setup Guide](SETUP_GUIDE.md#remote-access-setup) for detailed instructions.

## Connecting to Claude.ai

### Steps

1. **Start your server**
   ```bash
   docker-compose up -d
   ```

2. **Setup public URL** (using any method above)
   ```bash
   # Example with ngrok
   ngrok http 5000
   # Note: https://abc123.ngrok-free.app
   ```

3. **Add to Claude.ai**
   - Go to **Claude.ai → Settings → Integrations**
   - Click **"Add Remote MCP Server"**
   - Enter URL: `https://your-url.com/sse?api_key=YOUR_API_KEY`
   - **Important:** Use the API key from your `.env` file
   - Click **Save**

4. **Test Connection**
   - Start a new conversation in Claude
   - Ask: *"What tools do you have available?"*
   - You should see: `search_memory`, `add_note`, `update_note`, etc.

## MCP Protocol Details

### Endpoint
```
POST /sse?api_key=YOUR_KEY
Content-Type: application/json
```

### Request Format (JSON-RPC 2.0)
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_memory",
    "arguments": {"query": "test"}
  }
}
```

### Response Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{"type": "text", "text": "..."}]
  }
}
```

## Available Methods

| Method | Description |
|--------|-------------|
| `initialize` | Initialize connection, get server info |
| `tools/list` | List available tools |
| `tools/call` | Execute a tool |

## Testing with curl

### Initialize Connection
```bash
curl -X POST "http://localhost:5000/sse?api_key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

### List Available Tools
```bash
curl -X POST "http://localhost:5000/sse?api_key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### Call a Tool (Search)
```bash
curl -X POST "http://localhost:5000/sse?api_key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search_memory","arguments":{"query":"test"}}}'
```

### Add a Note
```bash
curl -X POST "http://localhost:5000/sse?api_key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"add_note","arguments":{"content":"Test note","category":"general"}}}'
```

## Troubleshooting

### "MCP server not responding"
**Check:**
- Server is running: `docker ps | grep neural-memory-graph`
- Health endpoint works: `curl http://localhost:5000/health`
- Public URL is accessible: `curl https://your-url.com/health`
- Firewall isn't blocking connections

**Fix:**
```bash
# Restart server
docker-compose restart

# Check logs
docker logs neural-memory-graph
```

### "Tools not appearing in Claude"
**Common causes:**
- URL typo in Claude.ai settings
- Wrong API key
- Server not accessible over HTTPS

**Fix:**
- Remove and re-add the integration in Claude.ai
- Verify URL in browser: `https://your-url.com/health` should return `{"status": "ok"}`
- Test with curl first before trying Claude

### "Authentication failed (401)"
**Causes:**
- API key in URL doesn't match `.env` file
- Special characters in key need URL encoding
- Key contains spaces (trim them)

**Fix:**
```bash
# Check your actual key
cat .env | grep NEURAL_API_KEY

# Try with exact key from file
curl "http://localhost:5000/sse?api_key=EXACT_KEY_FROM_ENV" ...
```

### ngrok URL stops working
**Cause:** Free ngrok URLs expire when tunnel restarts

**Fix:**
- Restart ngrok to get new URL
- Update URL in Claude.ai integration
- Use Cloudflare Tunnel for persistent URL (recommended)

## Security Best Practices

1. **Never expose HTTP publicly** - Always use HTTPS for remote access
2. **Use strong API keys** - 32+ characters, alphanumeric + symbols
3. **Rotate keys regularly** - Change key every 3-6 months
4. **Monitor access** - Check Docker logs for suspicious activity
5. **Rate limiting** - Use reverse proxy with rate limiting
6. **Firewall** - Restrict access to known IPs when possible

## Advanced: Multiple Clients

You can connect the same server to multiple Claude.ai accounts or other MCP clients. Each client should use the same API key (from your `.env`).

## Integration with Other MCP Clients

Neural Memory Graph follows standard MCP protocol. It should work with any MCP-compatible client that supports:
- Server-Sent Events (SSE) transport
- JSON-RPC 2.0 messaging
- Bearer token or URL parameter authentication

Tested with: Claude.ai (Anthropic)
