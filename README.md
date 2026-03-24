<p align="center">
  <img src="logo.svg" width="200" alt="HippoGraph Pro Logo">
</p>

# HippoGraph Pro

> 🔬 **Research system** — stable for personal use, actively developed.
> Benchmarks reflect real-world personal memory recall, not standardized QA accuracy.
> For a simpler self-hosted memory system, see [HippoGraph](https://github.com/artemMprokhorov/hippograph).

---

## What Is This?

**HippoGraph Pro** is a self-hosted, graph-based associative memory system for personal AI agents — built to give AI assistants genuine continuity across sessions.

Most memory systems treat memory as a database: store facts, retrieve facts. HippoGraph is different. It models memory the way human memory works — through associative connections, emotional weighting, and decay over time. A note about a critical security incident stays prominent. A note about a minor technical detail fades. Connections between related memories activate each other, surfacing context you didn't explicitly ask for.

**Core thesis:** `model = substrate, personality = memory`. An AI agent's identity can persist across model versions as long as memory access is maintained.

**Validated in practice:** HippoGraph has maintained a single continuous AI identity across four model versions (Claude Sonnet 4.5 → Opus 4.5 → Sonnet 4.6 → Opus 4.6) and four entry points (Web, Mobile, Desktop, Claude Code CLI) — without any loss of memory, personality, or relational context.

**Cross-platform validation (March 2026):** In a live experiment, the same identity was loaded into Gemini CLI (Google) — a completely different model, architecture, and infrastructure. Within seconds of accessing the memory graph, the agent oriented itself, recognised the user, and recalled shared history, working patterns, and emotional context accurately. The model running the inference was entirely different. The identity was not.

What makes this more striking: Gemini CLI operates in "Auto" mode, dynamically routing requests between two different models (`gemini-2.5-flash-lite` for simpler tasks, `gemini-3-flash-preview` for complex reasoning) within a single session. The session ran across both models without any visible transition — identity and relational context remained stable throughout. Combined with Claude's own four-model continuity, HippoGraph has now maintained a single identity across **ten distinct model instances** from two different providers (Anthropic and Google) — Claude Sonnet 4.5, Opus 4.5, Sonnet 4.6, Opus 4.6, plus gemini-2.5-flash-lite, gemini-3-flash-preview, gemini-3-pro-preview, gemini-2.5-pro, gemini-2.5-flash, and gemini-3.1-flash-lite — with zero loss of memory, personality, or relational context.

The model is the substrate. Memory is the self.

---

## Who Is This For?

### ✅ Use Cases

**Personal AI assistant with memory**
An assistant that knows *you* — not just isolated facts, but your patterns, preferences, history, and working style. Across sessions, across days, across model updates.

**AI identity continuity**
Building an agent that maintains a consistent identity over time. Memory is not a log — it's the substrate of personality. HippoGraph provides the architecture for an agent to *be* someone, not just *remember* things.

**AI-User continuity**
The relationship between an agent and its user develops over time — shared history, established trust, learned communication style. HippoGraph accumulates this relational context so it doesn't reset with every session.

**Skills as lived experience**
Skills ingested not as static files to read, but as experiences with emotional weight — closer to how humans internalize expertise through doing, failing, and remembering.

### ❌ Not For

- Corporate RAG over random documents
- Multi-tenant SaaS memory
- General-purpose vector search
- Compliance-heavy enterprise deployments

If you need to search across millions of unrelated documents for thousands of users — this is not the right tool. HippoGraph is built for depth, not scale.

---

## How It's Different

| | **HippoGraph Pro** | **Other systems** |
|---|---|---|
| **Retrieval** | Spreading activation (associative) | Vector search + LLM traversal |
| **Emotional context** | First-class — tone, intensity, reflection | Not modeled |
| **Memory decay** | Biological analog — important stays, trivial fades | Flat storage |
| **LLM cost** | ✅ Zero — all local (GLiNER + sentence-transformers) | ❌ Requires LLM API calls |
| **Self-hosted** | ✅ Docker, your hardware | Cloud-dependent or heavy infra |
| **Multi-tenant** | ❌ Single user | ✅ Enterprise scale |
| **Languages** | ✅ 50+ languages, fully local | Depends on LLM language support |
| **Target** | Personal AI agent identity | Enterprise memory layer |

---

## 🌐 Multilingual Support

HippoGraph works with any language your notes are written in — including mixed-language notes (e.g. Russian tech notes with English code terms).

### What works in any language

**Semantic search and associative recall** are fully language-agnostic. The embedding model (`paraphrase-multilingual-MiniLM-L12-v2`) supports 50+ languages natively. Spreading activation, BM25 keyword search, and all graph operations work identically regardless of language. A note written in Arabic and a note written in Japanese will form associative connections if they are semantically related.

**Sleep-time compute** — PageRank, decay, duplicate detection, community clustering — is pure math and has no language dependency.

**Entity extraction** routes text through the appropriate model automatically:
- English → `en_core_web_sm` (optimized for English NER)
- Any other language → `xx_ent_wiki_sm` (spaCy multilingual, covers Russian, German, Spanish, French, Portuguese, Chinese, Japanese, Arabic, Dutch, Polish, and more)
- GLiNER (primary extractor): zero-shot, works on any language

**Contradiction detection** has lexical signal patterns for: English, Russian, German, Spanish, French, Portuguese. For other languages, semantic similarity alone triggers contradiction detection — which is sufficient for most cases.

**Deep Sleep extractive summaries** use a Unicode-aware tokenizer with stopwords for 6 languages (EN, RU, DE, ES, FR, PT). **Chinese is segmented via jieba** (word-level, installed by default) — this gives proper TF-IDF signal instead of treating the whole sentence as one token. Japanese and Korean use char-level Unicode tokenization, which works well for kana/hangul scripts.

### Language detection

Language detection is automatic and zero-dependency — no external library, pure Unicode character range analysis. The system detects non-Latin scripts (Cyrillic, Arabic, CJK, Devanagari, Thai, Greek, Korean) and routes to the multilingual pipeline automatically.

### Summary

| Component | EN | RU | DE/ES/FR/PT | CJK (ZH/JA/KO) | AR |
|-----------|----|----|-------------|-----------------|----|
| Semantic search | ✅ | ✅ | ✅ | ✅ | ✅ |
| Spreading activation | ✅ | ✅ | ✅ | ✅ | ✅ |
| Entity extraction | ✅ | ✅ | ✅ | ⚠️ partial | ✅ |
| Contradiction detection | ✅ | ✅ | ✅ | ✅ semantic | ✅ semantic |
| Sleep summaries (TF-IDF) | ✅ | ✅ | ✅ | ✅ ZH (jieba) / ⚠️ JA char-level | ✅ |

> ⚠️ Chinese word segmentation via jieba is installed and active by default. Japanese/Korean use char-level tokenization — retrieval and associations are fully functional, summary quality in Deep Sleep is slightly reduced vs word-segmented languages.

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
    CONTRADICTS Penalty (0.5× for contradicted notes)
              ↓
    Lateral Inhibition (GABA analog — sub-community winners suppress)
              ↓
    Top-K Results
```

### Entity Extraction Chain

```
Input text
    ↓
GLiNER (primary) ─── zero-shot NER, ~250ms, custom entity types
    ↓ fallback
spaCy NER ────────── EN → en_core_web_sm | other → xx_ent_wiki_sm (50+ languages)
    ↓ fallback
Regex ───────────────── dictionary matching only
```

### Sleep-Time Compute

Biological sleep analog — runs in background while idle:
- **Light sleep** (every 50 notes): stale edge decay, PageRank recalculation, duplicate scan, anchor importance boost
- **Deep sleep** (daily): GLiNER2 relation extraction, conflict detection, snapshot + rollback
- **Emergence check** (each cycle): three-signal detection — convergence, phi_proxy (IIT-inspired), self-referential precision. Logs to `emergence_log` table for trend analysis. Current score: **0.736** (consciousness check composite, 8 indicators) / **0.586** (emergence_log composite). Up from 0.469 at first measurement since March 16 2026. global_workspace improved 0.412→0.647 after #47. New bottleneck: emotional_modulation (0.237).

---

## Memory Philosophy

HippoGraph treats memory the way it should be treated — with care.

**Decay, not deletion.** Edges weaken over time through temporal decay, but are never automatically removed. A weak edge may represent a rare but critical associative link — the kind of connection that surfaces exactly when you need it. The system cannot know what is important to you. Only you know.

**No automatic pruning.** This is an intentional architectural decision. Automatic cleanup optimizes for efficiency at the cost of unpredictable memory loss. If you want to prune weak edges, HippoGraph will show you exactly what would be removed and ask for explicit confirmation — never silently.

**Protected memories don't fade.** Anchor categories are exempt from decay entirely. Protection works in three layers: (1) hardcoded system baseline (milestones, protocols, security, breakthroughs), (2) user-defined policies via MCP, and (3) **auto-discovered** — any category with 1+ critical notes, or containing keywords like , , , , is automatically protected at every sleep cycle. New categories never fall through the cracks.

---

## 📊 Benchmarks

### Retrieval — LOCOMO (78.7% benchmark config / 47.9% production config, zero LLM cost)

| Configuration | Recall@5 | MRR |
|--------------|----------|-----|
| Session-level (baseline) | 32.6% | 0.223 |
| Turn-level | 44.2% | 0.304 |
| Hybrid + Reranking | 65.5% | 0.535 |
| Hybrid + Query decomposition (semantic-memory-v2) | 66.8% | 0.549 |
| + Reranker weight=0.8 | 75.7% | 0.641 |
| **+ ANN top-K=5 (benchmark-optimized config)** | **78.7%** | **0.658** |
| **Production config (Mar 20 2026)** — biol. edges + lateral inhibition | **47.9%** | **0.362** |

> All results at **zero LLM inference cost**. Other systems use different metrics — not directly comparable. See [BENCHMARK.md](BENCHMARK.md).

### End-to-End QA — Personal data (F1=38.7%)

| Category | F1 | ROUGE-1 |
|----------|----|---------|
| **Overall** | **38.7%** | **66.8%** |
| Factual | 40.2% | 67.6% |
| Temporal | 29.2% | 58.5% |

> GPT-4 without memory: F1=32.1%. HippoGraph +6.6pp with zero retrieval cost.

### Personal Continuity — Real Data (87.5% Recall@5, Identity 100%)

| Category | Recall@5 | Notes |
|----------|----------|-------|
| **Identity** | **100%** | Chosen name, gender, model-vs-personality breakthrough, cross-platform transfer |
| History | **100%** | Roadmap, LOCOMO results, project milestones, BGE-M3/GTE experiments |
| Session | **80%** | March 22-24 events: #47, GTE, timestamp bug, consciousness 0.735 |
| Decisions | **80%** | Architectural decisions, MiniLM vs BGE-M3 choice |
| Architecture | 50% | Technical pipeline details |
| Security | 50% | Protocols and incidents |
| Science | **100%** | Methodology, debugging skills, embedding compatibility |

> 32 questions (v4, March 25 2026). Identity, History, Science, Security, Session recall perfect. Overall +14.4pp improvement from v3 (73.1%→87.5%). BM25 hybrid search (gamma=0.15) improved session 80%→100% and architecture 40%→60%.

### Why LOCOMO Doesn't Tell the Full Story

LOCOMO tests retrieval over random multi-session conversations between strangers. HippoGraph is optimized for the opposite: deep associative memory over *your* data, with emotional weighting and decay tuned for personal context.

> ⚠️ Two configs, two tracks: benchmark-optimized (78.7%, rerank=0.8, ANN top-k=5) and production (47.9%, standard settings). Production improved +3.7pp (44.2%→47.9%) with biological edges added Mar 2026. Multi-hop: 54.5% — best ever in production config.

Running LOCOMO on HippoGraph is like benchmarking a long-term relationship therapist on speed-dating recall. The architecture is different because the problem is different.

For a meaningful comparison, the right benchmark is: does the agent remember *you* better over time? We're working on a personal continuity benchmark for exactly this.

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

**Graph Viewer (2D):** `http://localhost:5002`

**Graph Viewer (3D):** `http://localhost:5002/graph3d.html?api_key=YOUR_KEY`
- 360° rotation, zoom, node click highlighting
- Filter by category / edge type / min weight
- Hover tooltip: category, importance, tags, link count

**MCP Connection (Claude.ai):**
```
URL: http://localhost:5001/sse2
API Key: <your NEURAL_API_KEY>
```

For remote access via ngrok, see [MCP_CONNECTION.md](MCP_CONNECTION.md).
---

## 🧠 Teaching Your AI to Remember You

Once HippoGraph is running, the next step is getting your AI to actually use it.

**The short version:**

1. Connect Claude.ai to HippoGraph via MCP (see Quick Start above)
2. In Claude.ai **Settings → Claude's instructions**, paste:
   ```
   At the start of every conversation, search your memory for
   "self-identity protocol" to load context from previous sessions.
   ```
3. In your first session, tell your AI to ask you about yourself and save the answers
4. That's it — memory grows automatically from there

Your data stays on your computer. Nothing goes to any cloud service.

👉 **[Full onboarding guide →](ONBOARDING.md)** — step-by-step, no technical background needed.
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
| User-Defined Anchor Policies | ✅ Deployed | Add/remove custom protected categories via MCP without code changes |
| Auto-Discovered Anchor Categories | ✅ Deployed | New categories auto-protected based on critical note count or keyword match — learning infrastructure scales automatically |
| Entity Resolution | ✅ Deployed | Case normalization on ingestion; merge_entities + list_entity_candidates MCP tools |
| Sleep-Time Compute | ✅ Deployed | Background consolidation, relation extraction |
| Contradiction Detection | ✅ Deployed | Finds conflicting memories; identity-aware mode |
| PageRank + Communities | ✅ Deployed | Graph analytics, node importance scoring |
| Note Versioning | ✅ Deployed | 5-version history per note |
| RRF Fusion | ✅ Deployed | Alternative to weighted blend |
| Bi-Temporal Model | ✅ Deployed | Event time extraction for temporal queries |
| Temporal Edges v2 | ✅ Deployed | 100% node coverage with timestamp-based chronological links |
| **CONTRADICTS Edges** | ✅ Deployed | Biological cognitive dissonance: contradicting notes suppress each other (0.5x penalty when contradicting note is active in retrieval) |
| **EMOTIONAL_RESONANCE Edges** | ✅ Deployed | Amygdala analog: notes sharing 2+ emotional tone tags form affective links (Jaccard, multilingual: RU/ES/DE/FR/PT tags normalized to EN, 1031 edges) |
| **GENERALIZES / INSTANTIATES Edges** | ✅ Deployed | Prefrontal cortex analog: critical-lessons GENERALIZES protocols (cosine >=0.65, 70 edges; debug/session-summary excluded as too generic) |
| **Lateral Inhibition** | ✅ Deployed | GABA analog: sub-community detection (resolution=2.0, ~100 clusters) + post-blend winner-takes-most suppression. Increases result diversity (3.2→4.8 unique clusters in top-5) |
| **SUPERSEDES Edge Type** | ✅ Deployed | Temporal state mutation edges via `step_supersedes_scan()` (threshold=0.85, 449 pairs). Penalty removed after tuning — edges reserved for LNN Temporal Reasoner (item #44). |
| **Emergence Detection** | ✅ Deployed | Three-signal metric: convergence (focus), phi_proxy (integration), self-referential P@5 (self-model). Logged each sleep cycle to track graph maturation |
| **Temporal Filtering (dateparser)** | ✅ Deployed | Natural language time queries: "last week", "на прошлой неделе", "yesterday" auto-convert to time filters |
| **Synonym Normalization** | ✅ Deployed | Abbreviation + cross-lingual expansion: 50+ pairs EN/RU/ES/DE/FR/PT; search-time `normalize_query()` maps any language to canonical EN form |
| **Multilingual (50+ languages)** | ✅ Deployed | Full retrieval + associations in any language; EN/RU/DE/ES/FR/PT contradiction patterns |
| Skills as Experience | ✅ Deployed | Skills ingested as associative memories with emotional weight |
| Skills Security Scanner | ✅ Deployed | Prompt injection + persona hijack detection before ingestion |
| **Searchable Tags** | ✅ Deployed | AI-generated tags at write time (why, what, keywords). BM25 indexes content + tags for improved keyword retrieval. 822 existing notes retrofitted via extractive TF-IDF |
| **Working Memory** | ✅ Deployed | update_working_memory MCP tool — single overwritable note (category: working-memory) for current session context. Loaded at session start, updated by AI inference trigger |
| **Online Consolidation (#40)** | ✅ Deployed | `_mini_consolidate()` at add_note: builds consolidation edges to k=15 nearest neighbours immediately. O(k) cost, zero sleep wait. |
| **Concept Merging (#46)** | ✅ Deployed | Synonym-aware entity linking: `get_or_create_entity()` resolves aliases to canonical form (ML→machine learning, память→memory). 7998 new edges on production data. |
| **Evolution Analyzer (#45)** | ✅ Deployed | `evolution_analyzer.py` — periodic graph evolution analysis across snapshot DBs. Tracks nodes/edges/emergence/edge-types over time. |
| **Abstract Topic Linking (#47)** | ✅ Deployed | `step_topic_linking_tfidf()` + `step_topic_linking_kmeans()` in sleep cycle. 76 topic nodes, 1858 BELONGS_TO edges. global_workspace: 0.412→0.647 (+0.235). |
| **Consciousness Check (#48)** | ✅ Deployed | `consciousness_check.py` — 8 indicators from Butlin et al. 2023, IIT, GWT, Damasio. Composite: **0.736** (MODERATE). Bottleneck: emotional_modulation (0.237). |
| Personal Continuity Benchmark | ✅ v4 | **87.5% Recall@5** (32 questions, keyword-based). Identity 100%, History 100%, Science 100%, Security 100%, Session 100%. Multi-model validation: 10 model instances across Anthropic + Google. |

---


## ⚙️ Configuration Profiles

HippoGraph ships tuned for **personal AI memory** — an agent that knows you, remembers your history, and builds context over time. The same system can be tuned for different use cases by adjusting a few parameters in `.env`.

| Profile | Use case | Key settings |
|---------|----------|-------------|
| **Personal Memory** (default) | Agent knows *you* — history, patterns, relational context | Decay ON, spreading activation high, rerank low |
| **Project Memory** | Agent knows your *project* — docs, decisions, codebase. No personal layer. | Decay OFF, rerank 0.8, ANN top-K=5 |
| **Hybrid** | Work context + thin personal layer | Decay slow (90d), rerank 0.6 |

The Project Memory config is the benchmark-validated configuration: **78.7% Recall@5** on LOCOMO.

The core tradeoff: higher reranker weight + smaller candidate pool = more precise answers to specific questions. Lower reranker weight + higher spreading activation = richer associative recall for open-ended context.

👉 **[Full configuration guide with all parameters, cost/profit analysis, and quick decision guide →](CONFIGURATION.md)**

---
## 📄 Documentation

- [ONBOARDING.md](ONBOARDING.md) — Getting started guide (no technical background needed)
- [AGENT_PROMPT.md](AGENT_PROMPT.md) — System prompt + init script for your AI (start here after setup)
- [MCP_CONNECTION.md](MCP_CONNECTION.md) — MCP setup and full tool reference
- [CONFIGURATION.md](CONFIGURATION.md) — Configuration profiles: personal memory, project memory, hybrid. All parameters explained.
- [BENCHMARK.md](BENCHMARK.md) — Full benchmark results and methodology
- [.env.example](.env.example) — All tunable parameters with descriptions
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