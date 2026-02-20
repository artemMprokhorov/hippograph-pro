# HippoGraph - Personal Roadmap

**Target:** Single user, 500-2,000 notes, personal knowledge management + research
**Philosophy:** Keep all memories. Natural patterns over forced deletion. **Zero LLM cost as default.**
Runs on any hardware (laptop, mini-PC, 8GB RAM). LLM layer optional for users with GPU.
**Last Updated:** February 20, 2026 — **COMPLETED** ✅

---

## ✅ COMPLETED

### Core Infrastructure (Phase 1-2)
- [x] Graph-based architecture (nodes, edges, entities)
- [x] MCP protocol integration (Claude.ai)
- [x] ANN indexing (hnswlib) — O(log n) similarity search
- [x] In-memory graph cache — O(1) neighbor lookup
- [x] Activation normalization + damping
- [x] spaCy entity extraction + multilingual NER (EN + RU)
- [x] Test infrastructure (30 real tests)
- [x] Docker deployment on Mac Studio M3 Ultra

### Search & Retrieval
- [x] Blend scoring (α×semantic + β×spreading + γ×BM25 + δ×temporal)
- [x] BM25 keyword search (Okapi BM25, 8678 unique terms, zero-dependency)
- [x] Cross-encoder reranking (ms-marco-MiniLM-L-6-v2, +21% precision)
- [x] Bi-temporal model (t_event extraction, temporal overlap scoring)
- [x] Query temporal decomposition (signal stripping + chronological ordering)
- [x] Context window protection (brief/full modes)
- [x] Category, time range, entity type filters
- [x] Duplicate detection (similarity threshold)
- [x] Hub node penalty (entity count-based)
- [x] LOCOMO benchmark: **66.8% Recall@5** (zero LLM cost)
- [x] P@5 = 82%, Top-1 = 100% on internal benchmark

### Memory Features
- [x] Note versioning (5 versions, history, restore)
- [x] Importance scoring (critical/normal/low)
- [x] Emotional context (tone, intensity, reflection)
- [x] Batch knowledge import (196 skills imported)

### Visualization & Analytics
- [x] D3.js force-directed graph viewer + timeline
- [x] Graph metrics: PageRank + community detection (5 communities)
- [x] neural_stats: top PageRank nodes, community sizes, isolated count

### Memory Hygiene (All 5 Phases)
- [x] Phase 1: Test cleanup (24 notes deleted)
- [x] Phase 2: Session-end deduplication (24→14)
- [x] Phase 3: Skill isolation (58K entity edges removed)
- [x] Phase 4: Multilingual NER deployment
- [x] Phase 4.5: Entity re-extraction (587 notes)
- [x] Phase 5: Category normalization (93→68 categories)

**Current State:** 614 nodes, ~47K edges, ~1,700 entities, 68 categories, 8,678+ BM25 terms

---

## 🔥 HIGH PRIORITY — Next Development Cycle

### 1. ~~BM25 Hybrid Search~~ ✅ COMPLETED (Feb 12, 2026)
**Result:** Zero-dependency Okapi BM25. 8678 terms. Three-signal blend → four-signal with δ temporal.

### 2. ~~Reranking Pass~~ ✅ COMPLETED (Feb 12, 2026)
**Result:** Cross-encoder ms-marco-MiniLM-L-6-v2. +21.3% on LOCOMO. ~100ms latency.

### 3. ~~LOCOMO Benchmark~~ ✅ COMPLETED (Feb 12-18, 2026)
**Result:** Full adapter deployed. Optimization journey: 32.6% → 44.2% → 65.5% → **66.8% Recall@5**.
Hybrid granularity + reranking + bi-temporal + query decomposition. Zero LLM cost.
See [BENCHMARK.md](./BENCHMARK.md) for full results.

### 4. ~~Bi-Temporal Model~~ ✅ COMPLETED (Feb 18, 2026)
**Result:** t_event_start/end extraction via spaCy DATE + regex resolver. δ signal in blend formula.
Query temporal decomposition strips signal words for cleaner semantic search.

---

### 5. ~~LLM Generation Layer~~ → MOVED TO ENTERPRISE
Ollama requires GPU/M-series hardware — not available to typical personal users.
See ROADMAP_PRO.md Tier 2.5.

---

## 🎯 MEDIUM PRIORITY — Quality of Life

### 8. ~~Reciprocal Rank Fusion (RRF)~~ → MOVED TO ENTERPRISE
Current blend works well at personal scale (66.8% LOCOMO, 32/32 regression).
RRF optimization relevant for enterprise scale. See ROADMAP_PRO.md Tier 2.5.

### 4. ~~Sleep-Time Compute~~ ✅ COMPLETED (Feb 18, 2026)
**Result:** Zero-LLM graph maintenance daemon with 5-step cycle:
- [x] Thematic consolidation (semantic similarity ≥0.75 clustering)
- [x] Temporal chain detection (category-grouped sequences, 7-day gaps)
- [x] PageRank + community detection recalculation
- [x] Orphan detection (notes with ≤1 edges)
- [x] Stale edge decay (weight *= 0.95 for edges >90 days)
- [x] Near-duplicate scan (cosine ≥0.95, sliding window)
- [x] MCP tool integration (dry_run=True for safe preview)
Performance: 1.4s for 620 nodes, 58K edges. CLI + MCP accessible.

---

### 5. ~~CLI/TUI Interface~~ ✅ COMPLETED (Feb 18, 2026)
**Result:** `hippograph` CLI — search/add/stats/health commands. Color-coded scores,
brief/full modes, category filter. Config via ~/.hippograph.env. Aliases: `s`, `a`, `h`.

---

### 6. ~~Search Quality Monitoring~~ ✅ COMPLETED (Feb 18, 2026)
**Result:** search_logger.py logs every search to SQLite. Phase-level latency
tracking (embedding, ANN, spreading, BM25, temporal, rerank). Zero-result
detection. MCP tool `search_stats` for latency percentiles and quality metrics.

### 7. ~~Automated Regression Testing~~ ✅ COMPLETED (Feb 18, 2026)
**Result:** 12 queries, 32 expected notes, 100% P@5 baseline. Critical note checks
for security, consciousness, identity, benchmark retrieval. Avg 101ms latency.
Run: `python3 tests/regression_search.py -v` after each deploy.

---

## 🔬 RESEARCH — Future

### Multi-Agent Architecture → SEPARATE PROJECT
See dedicated multi-agent repo (TBD).

### Temporal Reasoning (Research Insight from Feb 18)
Temporal queries (36.5% on LOCOMO) require **LLM reasoning**, not better retrieval.
LOCOMO temporal Qs ask "what happened first?", "before or after?" — event ordering
that needs reading timestamps and reasoning, not similarity matching.
TReMu (Feb 2025) achieves 77.67% temporal via neuro-symbolic code generation.
Our path: Ollama + retrieved context + temporal chain-of-thought.

### ~~Real-Time Graph Visualization~~ ✅ COMPLETED (Feb 19-20, 2026)
**Result:** Full live notification system with login screen redesign.
- [x] Live graph updates via HTTP polling (MCP → pending_events queue → /api/poll-events → nginx → client fetch)
- [x] Toast notifications (green banner, page title update)
- [x] Login screen with HippoGraph branding (logo, connect flow, auto-login)
- [x] Disconnect/logout functionality
- [ ] Community highlighting in viewer (deferred to Pro)
- [ ] PageRank-based node sizing (deferred to Pro)
- [ ] Temporal playback improvements (deferred to Pro)

Key learnings: Flask-SocketIO cross-thread emit fails silently, WebSocket upgrade crashes Werkzeug,
polling transport loses server events. Simple HTTP polling through nginx proxy is the reliable solution.

---

## ❌ DEFERRED TO PRO

Moved to ROADMAP_PRO.md:
- Multi-tenant isolation
- Cloud managed service
- SSO/OAuth
- Horizontal scaling
- SOC2/GDPR compliance
- Multi-framework integration (LangChain, CrewAI)
- Bulk delete/cleanup operations
- Graph-wide rollback

---

## 📊 Competitive Position (Feb 18, 2026)

| Metric | HippoGraph | Mem0 | Zep | Letta | doobidoo |
|--------|-----------|------|-----|-------|----------|
| LLM Cost | **$0** | ~$0.01/note | ~$0.02/note | ~$0.05/note | $0 |
| Retrieval | Spread+Sem+BM25+Temporal | Vector+Graph | BM25+Sem+Graph | Agent-driven | Vector-only |
| LOCOMO | **66.8% R@5** | 66.9% J-score | N/A | 74.0% acc | N/A |
| Latency | 200-500ms | P95=1.44s | P95=300ms | varies | 5ms (cached) |
| Graph | ✅ Spreading | ✅ Mem0ᵍ | ✅ Temporal KG | ❌ | ❌ |
| Emotional | ✅ | ❌ | ❌ | ❌ | ✅ |
| Self-hosted | ✅ | ✅+Cloud | ✅+Cloud | ✅+Cloud | ✅ |

**Our niche:** Zero-LLM-cost, spreading activation, associative memory research. Nobody else does this.
