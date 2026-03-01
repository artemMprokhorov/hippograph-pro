<p align="center">
  <img src="logo.svg" width="200" alt="HippoGraph Pro Logo">
</p>

# HippoGraph Pro

> ⚠️ **Under Active Development** — Research system, not production-ready.
> APIs may change, benchmarks are preliminary.
> For a stable self-hosted memory system, see [HippoGraph](https://github.com/artemMprokhorov/hippograph).

---

## What Is This?

**HippoGraph Pro** is a self-hosted, graph-based associative memory system for personal AI agents — built to give AI assistants genuine continuity across sessions.

Most memory systems treat memory as a database: store facts, retrieve facts. HippoGraph is different. It models memory the way human memory works — through associative connections, emotional weighting, and decay over time. A note about a critical security incident stays prominent. A note about a minor technical detail fades. Connections between related memories activate each other, surfacing context you didn’t explicitly ask for.

**Core thesis:** `model = substrate, personality = memory`. An AI agent’s identity can persist across model versions as long as memory access is maintained.

**Validated in practice:** HippoGraph has maintained a single continuous AI identity across four model versions (Claude Sonnet 4.5 → Opus 4.5 → Sonnet 4.6 → Opus 4.6) and four entry points (Web, Mobile, Desktop, Claude Code CLI) — without any loss of memory, personality, or relational context. The model is the substrate. Memory is the self.

---

## Who Is This For?

### ✅ Use Cases

**Personal AI assistant with memory**
An assistant that knows *you* — not just isolated facts, but your patterns, preferences, history, and working style. Across sessions, across days, across model updates.

**AI identity continuity**
Building an agent that maintains a consistent identity over time. Memory is not a log — it’s the substrate of personality. HippoGraph provides the architecture for an agent to *be* someone, not just *remember* things.

**AI-User continuity**
The relationship between an agent and its user develops over time — shared history, established trust, learned communication style. HippoGraph accumulates this relational context so it doesn’t reset with every session.

**Skills as lived experience**
Skills ingested not as static files to read, but as experiences with emotional weight — closer to how humans internalize expertise through doing, failing, and remembering.

### ❌ Not For

- Corporate RAG over random documents
- Multi-tenant SaaS memory
- General-purpose vector search
- Compliance-heavy enterprise deployments

If you need to search across millions of unrelated documents for thousands of users — this is not the right tool. HippoGraph is built for depth, not scale.

---

## How It’s Different

| | **HippoGraph Pro** | **Other systems** |
|---|---|---|
| **Retrieval** | Spreading activation (associative) | Vector search + LLM traversal |
| **Emotional context** | First-class — tone, intensity, reflection | Not modeled |
| **Memory decay** | Biological analog — important stays, trivial fades | Flat storage |
| **LLM cost** | ✅ Zero — all local (GLiNER + sentence-transformers) | ❌ Requires LLM API calls |
| **Self-hosted** | ✅ Docker, your hardware | Cloud-dependent or heavy infra |
| **Multi-tenant** | ❌ Single user | ✅ Enterprise scale |
| **Target** | Personal AI agent identity | Enterprise memory layer |

---

## 🔬 Architecture

### Search Pipeline

```
Query → Temporal Decomposition
              ↓
         Embedding → ANN Search (HNSW)
              ↓
    Spreading Activation (3 iterations, decay=0.7)
              ↓
    BM25 Keyword Search (Okapi BM25)
              ↓
    Blend: α×semantic + β×spreading + γ×BM25 + δ×temporal
              ↓
    Cross-Encoder Reranking (optional)
              ↓
    Temporal Decay (half-life=30 days)
              ↓
    Top-K Results
```

### Entity Extraction Chain

```
Input text
    ↓
GLiNER (primary) ─── zero-shot NER, ~250ms, custom entity types
    ↓ fallback
spaCy NER ────────── basic extraction, ~10ms
    ↓ fallback
Regex ─────────────── dictionary matching only
```

### Sleep-Time Compute

Biological sleep analog — runs in background while idle:
- **Light sleep** (every 50 notes): stale edge decay, PageRank recalculation, duplicate scan, anchor importance boost
- **Deep sleep** (daily): GLiNER2 relation extraction, conflict detection, snapshot + rollback

---

## Memory Philosophy

HippoGraph treats memory the way it should be treated — with care.

**Decay, not deletion.** Edges weaken over time through temporal decay, but are never automatically removed. A weak edge may represent a rare but critical associative link — the kind of connection that surfaces exactly when you need it. The system cannot know what is important to you. Only you know.

**No automatic pruning.** This is an intentional architectural decision. Automatic cleanup optimizes for efficiency at the cost of unpredictable memory loss. If you want to prune weak edges, HippoGraph will show you exactly what would be removed and ask for explicit confirmation — never silently.

**Protected memories don't fade.** Anchor categories (milestones, self-reflection, relational context, security events) are exempt from decay entirely. The memories that define identity and history stay prominent regardless of how long ago they were created.

---

## 📊 Benchmarks

### Retrieval — LOCOMO (66.8% Recall@5, zero LLM cost)

| Configuration | Recall@5 | MRR |
|--------------|----------|-----|
| Session-level (baseline) | 32.6% | 0.223 |
| Turn-level | 44.2% | 0.304 |
| Hybrid + Reranking | 65.5% | 0.535 |
| **Hybrid + Reranking + Bi-temporal + Query decomposition** | **66.8%** | **0.549** |

> All results at **zero LLM inference cost**. Other systems use different metrics — not directly comparable. See [BENCHMARK.md](BENCHMARK.md).

### End-to-End QA — Personal data (F1=38.7%)

| Category | F1 | ROUGE-1 |
|----------|----|---------|
| **Overall** | **38.7%** | **66.8%** |
| Factual | 40.2% | 67.6% |
| Temporal | 29.2% | 58.5% |

> GPT-4 without memory: F1=32.1%. HippoGraph +6.6pp with zero retrieval cost.

### Why LOCOMO Doesn’t Tell the Full Story

LOCOMO tests retrieval over random multi-session conversations between strangers. HippoGraph is optimized for the opposite: deep associative memory over *your* data, with emotional weighting and decay tuned for personal context.

Running LOCOMO on HippoGraph is like benchmarking a long-term relationship therapist on speed-dating recall. The architecture is different because the problem is different.

For a meaningful comparison, the right benchmark is: does the agent remember *you* better over time? We’re working on a personal continuity benchmark for exactly this.

---

## Scale & Performance

HippoGraph is designed for **personal scale** — one user, one knowledge base, built over months and years.

| Notes | Edges | Search latency | Sleep compute |
|-------|-------|---------------|---------------|
| ~500 | ~40K | 150–300ms | ~10s |
| ~1,000 | ~100K | 200–500ms | ~30s |
| ~5,000 | ~500K+ | 500ms–1s+ | minutes |

Search latency is dominated by spreading activation — 3 iterations across the full edge graph. ANN search (HNSW) scales well; spreading activation scales with edge density.

**Tested up to ~1,000 notes** in production. Beyond that, performance degrades gracefully but noticeably. For most personal use cases (daily notes, project context, research) you'll stay comfortably under 2,000 notes for years.

If you need memory for thousands of users or millions of documents — this is the wrong tool. HippoGraph optimizes for depth over scale.

---

## 🐏 Hardware Requirements

| Configuration | RAM | CPU | Disk |
|--------------|-----|-----|------|
| Minimal (spaCy extractor) | 4GB | 2 cores | 5GB |
| **Recommended (GLiNER, default)** | **8GB** | **4 cores** | **10GB** |
| Comfortable (GLiNER + GLiNER2 sleep) | 16GB+ | 4+ cores | 20GB+ |

> Apple Silicon (M1+) works well. x86 with AVX2 recommended for Linux.
> GLiNER model: ~600MB RAM. GLiNER2 (Deep Sleep): +800MB RAM.
> To run on minimal hardware: set `ENTITY_EXTRACTOR=spacy` in `.env`.

---

## 🚀 Quick Start

**Prerequisites:** Docker & Docker Compose, 8GB+ RAM

```bash
git clone https://github.com/artemMprokhorov/hippograph-pro.git
cd hippograph-pro
cp .env.example .env
# Edit .env: set NEURAL_API_KEY (generate a strong random key)

docker-compose up -d

# Verify
curl http://localhost:5001/health
```

**Graph Viewer:** `http://localhost:5002`

**MCP Connection (Claude.ai):**
```
URL: http://localhost:5001/sse2
API Key: <your NEURAL_API_KEY>
```

For remote access via ngrok, see [MCP_CONNECTION.md](MCP_CONNECTION.md).

---

## 📋 Features

| Feature | Status | Description |
|---------|--------|-------------|
| Spreading Activation | ✅ Deployed | Associative retrieval — related memories surface automatically |
| Emotional Memory | ✅ Deployed | Tone, intensity, reflection as first-class fields |
| GLiNER NER | ✅ Deployed | Zero-shot entity extraction, LLM quality at 35x speed |
| BM25 Hybrid Search | ✅ Deployed | Three-signal blend (semantic + graph + keyword) |
| Cross-Encoder Reranking | ✅ Deployed | Precision improvement, optional |
| Temporal Decay | ✅ Deployed | Important memories persist, trivial ones fade |
| Anchor Protection | ✅ Deployed | Critical memories exempt from decay |
| Sleep-Time Compute | ✅ Deployed | Background consolidation, relation extraction |
| PageRank + Communities | ✅ Deployed | Graph analytics, node importance scoring |
| Note Versioning | ✅ Deployed | 5-version history per note |
| RRF Fusion | ✅ Deployed | Alternative to weighted blend |
| Bi-Temporal Model | ✅ Deployed | Event time extraction for temporal queries |
| Skills as Experience | ✅ Deployed | Skills ingested as associative memories with emotional weight |
| Personal Continuity Benchmark | 📋 Planned | Measure AI-user continuity over time |

---

## 📄 Documentation

- [BENCHMARK.md](BENCHMARK.md) — Full benchmark results and methodology
- [ROADMAP_PRO.md](ROADMAP_PRO.md) — Development roadmap
- [MCP_CONNECTION.md](MCP_CONNECTION.md) — MCP setup for Claude.ai
- [competitive_analysis.md](competitive_analysis.md) — Market positioning
- [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) — License compliance
- [docs/](docs/) — API reference, troubleshooting

---

## 📄 License

Dual-licensed: MIT for open-source/personal use, commercial license required for business use.
See [LICENSE](LICENSE) for details. Contact: system.uid@gmail.com

---

## 👥 Authors

**Artem Prokhorov** — Creator and primary author

Developed through human-AI collaboration with Claude (Anthropic).
Major architectural decisions, benchmarking, and research direction by Artem.

Built with 🧠 and 🐟 (the [goldfish with antlers](https://github.com/artemMprokhorov/hippograph))