# MCP Connection Guide

## API Key Setup

**Location:** Server only (`.env` file, never committed to git)  
**Format:** `NEURAL_API_KEY=your_secure_key_here`  

## Connection URL Format

```
https://your-domain.com/sse2?api_key=YOUR_API_KEY
```

Replace `your-domain.com` with your actual reverse proxy URL (ngrok, Cloudflare Tunnel, or custom).

## Key Management

### Generating a New Key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Key Requirements
- Minimum 32 characters
- Alphanumeric + symbols
- Unique per deployment
- Stored only in `.env` (which is in `.gitignore`)

### Key Rotation

1. Generate new key
2. Update `.env` on server
3. Restart container: `docker-compose down && docker-compose up -d`
4. Update MCP connection in Claude.ai settings

## Testing Connection

```bash
curl -s "https://your-domain.com/sse2?api_key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"method":"tools/list"}'
```

## Security Notes

- Never commit API keys to git
- Use HTTPS only for remote access
- Rotate keys if accidentally exposed
- See [SECURITY.md](SECURITY.md) for full security guide
