# HippoGraph Pro — Configuration Guide

HippoGraph ships with defaults tuned for **personal AI memory** — an agent that knows you, remembers your history, and builds relational context over time. The same system can be tuned for different use cases by adjusting parameters in your `.env` file.

---

## The Three Profiles

### Profile 1 — Personal AI Memory (default)

The agent knows *you*. It remembers what you’ve discussed, how you work, what matters to you. Spreading activation surfaces connections you didn’t explicitly ask for.

**Best for:** Personal assistant, AI identity continuity, long-term AI-user relationship.

```env
# Personal Memory (default — no changes needed)
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
ENTITY_EXTRACTOR=gliner
BLEND_ALPHA=0.7
BLEND_GAMMA=0.15
RERANK_ENABLED=true
RERANK_WEIGHT=0.5
RERANK_TOP_N=20
INHIBITION_STRENGTH=0.05
HALF_LIFE_DAYS=30
LATE_CHUNKING_ENABLED=true
LC_MODE=parent
```

**What you get:**
- Temporal decay — important memories stay prominent, trivial ones fade
- Associative retrieval — related memories surface without explicit query
- Overlap chunking — long notes split into overlapping chunks for fine-grained recall
- Identity continuity across sessions and model versions

**What you give up:**
- Slightly lower precision on specific factual queries vs benchmark-optimized config

---

### Profile 2 — Project Memory (pure task focus)

The agent knows your *project*, not you. Optimized for precision: specific question → most relevant document.

**Best for:** Project knowledge base, technical documentation assistant, research context.

```env
# Project Memory
BLEND_ALPHA=0.5
BLEND_GAMMA=0.15
RERANK_ENABLED=true
RERANK_WEIGHT=0.8
RERANK_TOP_N=5
INHIBITION_STRENGTH=0.05
HALF_LIFE_DAYS=36500
# effectively disables decay (100 years)
DISABLE_CATEGORY_DECAY=true
```

**What you get:**
- Higher retrieval precision — exact answers to specific questions
- Notes don’t fade — all project knowledge stays equally accessible
- Benchmark-validated: 78.7% Recall@5 on LOCOMO with this config

**What you give up:**
- No emotional context or personal history
- No associative “unexpected connection” surfacing

---

### Profile 3 — Hybrid (work context + thin personal layer)

The agent knows the project and has a light model of who you are.

**Best for:** Work assistant where some personal context is useful but task execution is primary.

```env
# Hybrid
BLEND_ALPHA=0.6
BLEND_GAMMA=0.15
RERANK_ENABLED=true
RERANK_WEIGHT=0.6
RERANK_TOP_N=10
INHIBITION_STRENGTH=0.05
HALF_LIFE_DAYS=90
```

---

## Parameter Reference

### Retrieval — Blend Weights

The pipeline combines three signals. Their weights control relative contribution.

| Parameter | Default | Signal | Description |
|-----------|---------|--------|-------------|
| `BLEND_ALPHA` | `0.7` | Semantic | Pure embedding similarity. How close query is to note in vector space. |
| `BLEND_GAMMA` | `0.15` | BM25 | Keyword overlap. Exact term matching. Spreading activation gets remainder (1-α-γ). |

> Spreading activation weight = `1 - BLEND_ALPHA - BLEND_GAMMA`. Default: 0.15.

**Cost/Profit:**
- Higher `BLEND_ALPHA` → more direct semantic matching, less associative
- Higher `BLEND_GAMMA` → better exact-term recall (technical terms, identifiers)
- For project memory: increase α, decrease γ. For personal memory: keep defaults.

---

### Retrieval — Reranking

| Parameter | Default | Description |
|-----------|---------|-------------|
| `RERANK_ENABLED` | `true` | Enable cross-encoder reranking (+precision, ~100ms latency). |
| `RERANK_MODEL` | `BAAI/bge-reranker-v2-m3` | Cross-encoder model. Apache 2.0. |
| `RERANK_WEIGHT` | `0.5` | How much reranker influences final ranking (0.0–1.0). Higher = reranker dominates. |
| `RERANK_TOP_N` | `20` | Candidate pool size for reranking. Lower = tighter, more precise set. |

**Cost/Profit:**
- High `RERANK_WEIGHT` (0.7–0.9) + low `RERANK_TOP_N` (5–10) → maximum precision, best for factual queries
- Low `RERANK_WEIGHT` (0.3–0.4) + high `RERANK_TOP_N` (15–20) → broader associative recall
- Reranking adds ~50–150ms. `RERANK_ENABLED=false` disables it entirely.

---

### Retrieval — Spreading Activation

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ACTIVATION_ITERATIONS` | `3` | Spreading activation iterations. More = deeper graph traversal. |
| `ACTIVATION_DECAY` | `0.7` | Activation decay per hop. Lower = faster falloff. |
| `INHIBITION_STRENGTH` | `0.05` | Lateral inhibition strength — suppresses weaker nodes within each community. 0 = off. |

---

### Memory Decay

| Parameter | Default | Description |
|-----------|---------|-------------|
| `HALF_LIFE_DAYS` | `30` | How fast edge weights decay. 30 days = note from a month ago has half the edge weight. Increase for slower forgetting. |
| `DISABLE_CATEGORY_DECAY` | `false` | Override: disable decay for protected anchor categories. Always `true` in benchmark runs. |

**Cost/Profit:**
- Short half-life → natural memory behavior, important stays prominent, old knowledge fades
- Long half-life / disable → everything equally accessible, higher precision on direct queries
- For project memory: set `HALF_LIFE_DAYS=36500` (effectively off)
- For personal memory: keep default 30 days

---

### Late Chunking (Overlap Chunking)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `LATE_CHUNKING_ENABLED` | `false` | Enable overlap chunking for long notes. Strongly recommended — +21.7pp LOCOMO. |
| `LC_MODE` | `parent` | Chunking mode. `parent` = D1 production config (chunks + parent note). |
| `LC_CHUNK_CHARS` | `400` | Target chunk size in characters. |
| `LC_OVERLAP_CHARS` | `200` | Overlap between adjacent chunks (50%). |
| `LC_MIN_NOTE_CHARS` | `300` | Minimum note length to trigger chunking. |

> ⚠️ Enable this. `LATE_CHUNKING_ENABLED=true` + `LC_MODE=parent` is the production config that achieves 91.1% LOCOMO Recall@5.

---

### Entity Extraction

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ENTITY_EXTRACTOR` | `gliner` | Entity extraction model. `gliner` = GLiNER (~250ms, 600MB RAM, best quality). `spacy` = fast (~10ms, ~80MB). `regex` = minimal. |
| `GLINER_MODEL` | `urchade/gliner_multi-v2.1` | GLiNER model variant. |
| `GLINER_THRESHOLD` | `0.4` | Confidence threshold for GLiNER entity detection. |

**Cost/Profit:**
- `gliner` → richer entity graph, better spreading activation, requires 8GB+ RAM
- `spacy` → minimal hardware (4GB RAM), faster ingestion, less rich graph
- For minimal hardware: `ENTITY_EXTRACTOR=spacy`

---

### Embedding Model

| Parameter | Default | Description |
|-----------|---------|-------------|
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Sentence-transformer model for vector search. |

**Model options (from lightest to heaviest):**

| Model | Dims | RAM | Languages | Notes |
|-------|------|-----|-----------|-------|
| `all-MiniLM-L6-v2` | 384 | ~80MB | English only | Minimal hardware |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | ~120MB | 50+ | **Default — good balance** |
| `BAAI/bge-m3` | 1024 | ~2.2GB | 100+ | **Production quality — 91.1% LOCOMO** |

> ⚠️ Changing `EMBEDDING_MODEL` requires re-indexing all notes:
> ```bash
> docker exec hippograph python3 src/reindex_embeddings.py
> ```

---

### Sleep-Time Compute

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SLEEP_INTERVAL_HOURS` | `6` | Run sleep_compute every N hours. 0 = disabled. |
| `SLEEP_NOTE_THRESHOLD` | `50` | Also trigger after N new notes added. 0 = disabled. |

---

## Quick Decision Guide

```
I want the agent to know ME over time
    → Profile 1 (Personal Memory, default)
    LATE_CHUNKING_ENABLED=true, LC_MODE=parent

I want the agent to know my PROJECT / codebase / docs
    → Profile 2 (Project Memory)
    RERANK_WEIGHT=0.8, RERANK_TOP_N=5, HALF_LIFE_DAYS=36500

I want work context + light personal layer
    → Profile 3 (Hybrid)
    HALF_LIFE_DAYS=90, RERANK_WEIGHT=0.6

I’m running on minimal hardware (4GB RAM)
    → Any profile + ENTITY_EXTRACTOR=spacy + EMBEDDING_MODEL=all-MiniLM-L6-v2
    Leave RERANK_ENABLED=false (saves ~500MB RAM)

I want maximum retrieval precision (benchmark mode)
    → RERANK_WEIGHT=0.8, RERANK_TOP_N=5, HALF_LIFE_DAYS=36500
    EMBEDDING_MODEL=BAAI/bge-m3 (78.7% Recall@5 with MiniLM, ~91% with BGE-M3)
```

---

## Applying Changes

All parameters live in `.env`. After editing:

```bash
# Full restart required — docker restart does NOT reload .env
docker-compose down && docker-compose up -d
```

> ⚠️ `docker-compose restart` does **not** reload environment variables. Always use `down/up`.

---

## What Doesn’t Change Between Profiles

- **No automatic deletion** — notes are never silently removed. Decay weakens edges, never deletes nodes.
- **Anchor protection** — `self-reflection`, `protocol`, `security`, `milestone` and other protected categories never decay.
- **Zero LLM cost** — all retrieval runs locally. No API calls required regardless of profile.
- **Single user** — HippoGraph is not multi-tenant. All profiles assume one user, one knowledge base.

---

*For full benchmark results and methodology, see [BENCHMARK.md](BENCHMARK.md).*  
*For setup and MCP connection, see [ONBOARDING.md](ONBOARDING.md).*  
*All parameters with defaults: see [.env.example](.env.example).*