# Graph Viewer - Setup & Usage

## Overview

HippoGraph includes an interactive D3.js graph visualization accessible at `http://localhost:5002`.

The viewer loads **all nodes and edges** via a REST API endpoint, providing a complete visual map of your knowledge graph.

## Architecture

```
Browser (port 5002)
    ↓
  nginx (static files + API proxy)
    ↓  /api/*
  Flask (port 5000)
    ↓
  SQLite + Graph Cache
```

- **nginx** serves the HTML/JS viewer and proxies `/api/` requests to Flask
- **Flask** provides REST endpoints for graph data
- **No MCP needed** — viewer uses standard HTTP GET requests

## Quick Start

### 1. Start Server

```bash
docker-compose up -d
```

### 2. Open Viewer

Navigate to `http://localhost:5002` (or `http://<server-ip>:5002` on local network).

### 3. Configure Connection

Enter your API key from `.env` and click "Connect & Load".

The viewer loads all nodes with brief previews. Click any node to see full content.

## REST API Endpoints

### GET /api/graph-data

Returns all nodes and edges for visualization.

**Parameters:**
- `api_key` (required) — Your NEURAL_API_KEY
- `brief` (optional, default: `true`) — Return truncated content (first line, max 200 chars)

**Response:**
```json
{
  "nodes": [
    {
      "id": 1,
      "category": "self-reflection",
      "importance": "normal",
      "timestamp": "2026-01-22T...",
      "emotional_tone": "curiosity",
      "emotional_intensity": 6,
      "preview": "First line of note content...",
      "full_length": 1234
    }
  ],
  "edges": [
    {"source": 1, "target": 2, "weight": 0.75, "type": "semantic"}
  ],
  "stats": {"total_nodes": 593, "total_edges": 48108}
}
```

### GET /api/node/<id>

Returns full content for a single node (on-demand detail loading).

**Parameters:**
- `api_key` (required)

## Viewer Features

- **D3.js force-directed layout** — Interactive graph with drag, zoom, pan
- **Category color coding** — Visual distinction by note type
- **Search** — Filter nodes by content
- **Category filter** — Show specific categories
- **Timeline slider** — Animate graph growth over time
- **Link toggles** — Show/hide entity vs semantic connections
- **Link weights** — Color-coded connection strength
- **Node click** — Load full note content via REST API
- **Performance** — Links capped at 5000 (top by weight) for browser performance

## Security

- API key required for all REST endpoints
- Credentials stored in browser localStorage only (7-day expiry)
- Never committed to git
- CSP headers restrict connections to known origins
- See [SECURITY.md](SECURITY.md) for full details

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "unauthorized" error | Check API key matches `.env` |
| No nodes loaded | Verify server is healthy: `curl http://localhost:5001/health` |
| Graph is slow | Normal for 40K+ edges; links auto-capped at 5000 |
| CORS errors | Check nginx CSP in `nginx.conf` |

---

**Last Updated:** Feb 5, 2026
