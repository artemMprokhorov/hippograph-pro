<p align="center">
  <img src="logo.svg" width="200" alt="Neural Memory Graph Logo">
</p>

# HippoGraph Pro

**Personal Knowledge Management with Semantic Graph Memory — Pro Edition**

A self-hosted MCP (Model Context Protocol) server that adds persistent, graph-based semantic memory to AI assistants. Pro edition adds RRF fusion, LLM-enhanced processing via Ollama, and advanced graph analytics.

Built on top of [HippoGraph](https://github.com/artemMprokhorov/hippograph) personal edition.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

---

## ✨ Features

**Graph-Based Memory Architecture:**
- 🕸️ **Automatic Entity Extraction** — Identifies people, concepts, projects from your notes (regex + multilingual spaCy NER)
- 🔗 **Semantic Connections** — Discovers related notes through shared entities
- 📊 **Knowledge Graph** — View how your ideas connect and relate
- 🎯 **Spreading Activation Search** — Find notes through association chains, not just keywords
- 🔀 **Blend Scoring** — Three-signal retrieval: semantic similarity + graph activation + BM25 keyword matching (tunable α/β/γ weights)
- 🌍 **Multilingual Support** — English + Russian entity extraction with automatic language detection

**Graph Visualization & Web UI:**
- 🔐 **Login Screen** — Branded login with auto-reconnect (7-day credential storage)
- 🌐 **Interactive Graph Viewer** — D3.js force-directed layout at `http://localhost:5002`
- 🎨 **Category Color Coding** — Visual distinction by note type
- ⏱️ **Timeline Animation** — Watch your knowledge graph grow over time
- 🔍 **Click-to-Detail** — Load full note content on demand
- 📡 **Live Notifications** — Real-time toast alerts when notes are added/deleted via MCP

**Technical Features:**
- 384-dimensional semantic embeddings (paraphrase-multilingual-MiniLM-L12-v2)
- SQLite graph database with nodes, edges, and entities
- Automatic relationship detection between notes
- MCP protocol integration for AI assistants
- **Multilingual NER** — en_core_web_sm (English) + xx_ent_wiki_sm (Russian/multilingual) with automatic language routing
- **Temporal decay** for recency-weighted search
- **Importance scoring** (critical/normal/low) with activation boost
- **Duplicate detection** with similarity thresholds (blocks >95%, warns >90%)
- **BM25 keyword search** — Okapi BM25 inverted index for exact term matching, integrated into blend scoring
- **Cross-encoder reranking** — Optional ms-marco-MiniLM reranker for precision improvement on top-N candidates
- **Context window protection** — brief/full detail modes, token estimation, progressive loading
- **Note versioning** — auto-save history, restore previous versions
- **Graph visualization** — D3.js interactive viewer with REST API
- **Sleep-time compute** — Zero-LLM graph maintenance: consolidation, PageRank, orphan detection, stale decay, duplicate scan (MCP tool)
- **Bi-temporal model** — Event time extraction for temporal query answering
- **LOCOMO benchmark** — 66.8% Recall@5 at zero LLM cost
- Docker-ready deployment (multi-architecture: amd64 + arm64)

---

## 🎯 Use Cases

- 📚 **Long-term Projects** — Remember architectural decisions, preferences, context across sessions
- 🔬 **Research Workflows** — Build semantic knowledge base, connect related findings automatically
- 💼 **Business Context** — Maintain understanding of workflows, track project relationships
- 🧠 **Personal Knowledge Management** — Second brain with automatic idea connections
- 🛠️ **Developer Productivity** — Track codebase details, related bugs and solutions

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB+ RAM, 3GB+ disk space
- For remote access: Reverse proxy (ngrok, Cloudflare Tunnel, or custom)

### 1. Clone & Configure

```bash
git clone https://github.com/artemMprokhorov/hippograph-pro-pro.git
cd hippograph
cp .env.example .env
# Edit .env and set a strong NEURAL_API_KEY (32+ characters)
```

### 2. Start Server

```bash
docker-compose up -d
```

The server will:
- Download embedding models (~2GB on first run)
- Download spaCy models for entity extraction (en + multilingual)
- Initialize SQLite database
- Start API on `http://localhost:5001`
- Start Graph Viewer on `http://localhost:5002`

### 3. Verify Installation

```bash
curl http://localhost:5001/health
# Expected: {"status": "ok", "version": "2.0.0"}
```

### 4. Open Graph Viewer

Open `http://localhost:5002` in your browser. Enter your API endpoint URL
(`http://localhost:5001/sse2`) and the API key you set in `.env`.

### 5. Setup Remote Access (Optional)

For Claude.ai integration or remote use, you need a public HTTPS URL.  
See [Setup Guide](docs/SETUP_GUIDE.md) for options:
- **ngrok** - Quick testing (free tier)
- **Cloudflare Tunnel** - Persistent URL (recommended)
- **Custom reverse proxy** - Nginx, Caddy, etc.

### 6. Connect to Claude.ai

Once you have a public URL:
1. Go to **Claude.ai → Settings → Integrations**
2. **Add Remote MCP Server**
3. Enter: `https://your-domain.com/sse?api_key=YOUR_API_KEY`

See [MCP Integration Guide](docs/MCP_INTEGRATION.md) for details.

---

## 📋 System Requirements

### Minimum (for ~500-1000 notes)
- **RAM:** 2GB minimum (breakdown below)
  - sentence-transformers model: ~500 MB
  - spaCy NER models: ~25 MB (en_core_web_sm + xx_ent_wiki_sm)
  - FAISS index: ~1-2 MB per 1000 nodes
  - Graph cache: ~1-2 MB per 20K edges
  - Python runtime + dependencies: ~300 MB
- **Disk:** 2GB free (Docker image + models)
- **CPU:** Modern x64/ARM64 processor (no GPU needed)
- **OS:** Linux, macOS, Windows (with Docker)

### Recommended (for 5000+ notes)
- **RAM:** 4GB+ (for larger graphs and concurrent requests)
- **Disk:** 5GB+ (for database growth)
- **SSD:** Highly recommended for faster SQLite operations
- **CPU:** 2+ cores for better MCP concurrency

### Performance Notes
- **ANN Index (FAISS):** Loads all node embeddings into RAM at startup
  - Scales: ~400 KB per 1000 nodes (384-dim vectors)
- **Graph Cache:** Loads all edges into RAM for O(1) lookup
  - Scales: ~1 MB per 20K edges (bidirectional dict)
- **Cold Start:** ~2-5 seconds to rebuild indices on container restart
- **Search Speed:** O(log n) with ANN index, fully in-memory graph traversal

---

## 🛠️ Available MCP Tools

| Tool | Description |
|------|-------------|
| `search_memory` | Semantic search with spreading activation. Supports `detail_mode` (brief/full), `max_results` limit, category/time/entity filters |
| `add_note` | Save note with auto-embedding, entity extraction, and duplicate detection |
| `update_note` | Modify existing note, recompute connections |
| `delete_note` | Remove note and its graph relationships |
| `set_importance` | Set note importance (critical/normal/low) for search ranking |
| `find_similar` | Check for similar notes before adding (deduplication) |
| `neural_stats` | View memory statistics and graph metrics |
| `get_graph` | Get connections for a specific note |
| `get_note_history` | View version history for a note |
| `restore_note_version` | Restore note to a previous version |

### REST API (Graph Viewer)

| Endpoint | Description |
|----------|-------------|
| `GET /api/graph-data` | All nodes and edges for visualization |
| `GET /api/node/<id>` | Full content for a single node |
| `GET /health` | Server health check |

---

## 🏗️ Architecture

### Graph Database Schema

```
nodes (notes)
├── id, content, category
├── timestamp, embedding
├── importance, last_accessed
└── temporal decay tracking

edges (connections)
├── source_id → target_id
├── weight, edge_type
└── created_at

note_versions (history)
├── note_id, version_number
├── content snapshot
└── last 5 versions kept

entities (extracted concepts)
├── name, entity_type
└── linked to multiple nodes

node_entities (relationships)
└── many-to-many linking
```

### How It Works

```
┌─────────────┐
│   Add Note  │
└──────┬──────┘
       │
       ├─→ Generate Embedding (384D vector)
       ├─→ Extract Entities (spaCy NER + regex)
       ├─→ Find Related Notes (similarity + shared entities)
       ├─→ Check Duplicates (>95% blocks, >90% warns)
       └─→ Create Graph Edges (semantic connections)

Search Query
       ↓
    Embedding → Similarity Search → Spreading Activation → BM25 Keyword
       ↓              ↓                      ↓                    ↓
    Vector DB    Related Nodes      Connection Chains     Inverted Index
                                                                 ↓
                              Blend Scoring (α×semantic + β×spread + γ×BM25)
                                           ↓
                              Cross-Encoder Reranking (optional, top-20)
                                           ↓
                                  Temporal Decay + Importance Boost
```

---

## 🔧 Configuration

Edit `.env` to customize behavior:

```bash
# Entity extraction mode
ENTITY_EXTRACTOR=spacy  # Options: regex, spacy

# Spreading activation
ACTIVATION_ITERATIONS=3
ACTIVATION_DECAY=0.7

# Blend scoring (four-signal balance)
# BLEND_ALPHA=0.6  # Semantic similarity weight (default 0.6)
# BLEND_GAMMA=0.15 # BM25 keyword weight (default 0.0 = disabled)
# BLEND_DELTA=0.1  # Temporal weight (default 0.0, auto-enabled for temporal queries)
# β = 1 - α - γ - δ  # Spreading activation gets remainder

# Temporal decay (days)
HALF_LIFE_DAYS=30

# Deduplication threshold
SIMILARITY_THRESHOLD=0.5
```

---

## 🔒 Security

**⚠️ Research/Personal Project Notice:**  
This is not audited for production use with sensitive data.

**Best Practices:**
- Use strong API keys (32+ characters, alphanumeric + symbols)
- Rotate keys periodically
- Use HTTPS (never expose HTTP publicly)
- Restrict server access (firewall/VPN)
- Review [SECURITY.md](SECURITY.md) for details

---

## 📖 Documentation

- [Setup Guide](docs/SETUP_GUIDE.md) — Detailed installation and configuration
- [API Reference](docs/API_REFERENCE.md) — Complete MCP tools documentation
- [MCP Integration](docs/MCP_INTEGRATION.md) — Connect to Claude.ai and other clients
- [Graph Features](docs/GRAPH_FEATURES.md) — Spreading activation and entity linking
- [Troubleshooting](docs/TROUBLESHOOTING.md) — Common issues and solutions

---

## 📦 Project Structure

```
hippograph/
├── src/
│   ├── server.py              # Flask app entry
│   ├── database.py            # Graph database layer
│   ├── graph_engine.py        # Spreading activation + blend scoring
│   ├── bm25_index.py          # Okapi BM25 keyword search index
│   ├── reranker.py            # Cross-encoder reranking pass
│   ├── sleep_compute.py       # Zero-LLM graph maintenance daemon
│   ├── entity_extractor.py    # spaCy NER + regex extraction
│   ├── stable_embeddings.py   # Embedding model
│   └── mcp_sse_handler.py     # MCP protocol
├── scripts/
│   ├── backup.sh              # Database backup
│   ├── restore.sh             # Database restore
│   ├── recompute_embeddings.py
│   └── re_extract_entities.py # Rebuild entity graph with current NER
├── web/
│   └── index.html             # D3.js graph viewer
├── docs/                      # Documentation
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## 🤝 Contributing

Contributions welcome! This project explores semantic memory systems and knowledge graphs.

**Areas for Contribution:**
- Additional entity extraction methods (LLM-based)
- Graph visualization tools
- Performance optimizations
- Documentation improvements

---

## 📄 Licensing

This project is dual-licensed:

- Open-source / personal / non-commercial use: MIT License  
  See the <LICENSE> file for full terms.
- Commercial use, SaaS integration, proprietary redistribution, closed-source derivative works, or any use that does not comply with MIT terms: requires a separate commercial license.  
  Contact: [system.uid@gmail.com] for pricing, terms, and licensing agreement.

If you plan to use this software in a product, service, internal enterprise deployment, or any context where MIT obligations (copyright notice preservation, etc.) are undesirable or incompatible, obtain explicit written permission via commercial license before proceeding.

This dual-licensing model allows free open-source access while reserving commercial rights to the original author.

---

## 👥 Authors

**Artem Prokhorov** — Creator and primary author

**Development approach:** This system emerged through intensive human-AI collaboration. Major architectural contributions—including graph-based spreading activation, entity extraction systems, and technical documentation—were developed iteratively with Claude (Anthropic).

Built with 🧠 by Artem Prokhorov
