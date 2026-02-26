# HippoGraph Pro — Roadmap

**Repository:** github.com/artemMprokhorov/hippograph-pro
**Base:** Built on top of HippoGraph Personal (same container, same memory)
**Philosophy:** Add capabilities, don't rewrite foundation. Zero LLM cost as core advantage.
**Last Updated:** February 25, 2026

---

## Phase 1 — Quick Wins ✅ COMPLETED

### 1. Reciprocal Rank Fusion (RRF) ✅
- [x] Implement RRF fusion as alternative to weighted blend (src/rrf_fusion.py)
- [x] A/B test: RRF vs current blend on regression suite (both 32/32 100% P@5)
- [x] Config: `FUSION_METHOD=blend|rrf` (default: blend)

### 2. Graph Viewer Enhancements ✅
- [x] Community highlighting (color clusters from NetworkX detection)
- [x] PageRank-based node sizing (important nodes = bigger)
- [ ] Community labels overlay (deferred)

### Bugfix
- [x] Fixed graph-data API 500: metrics.is_computed property called as method

---

## Phase 2 — Entity Extraction & Benchmarking ✅ COMPLETE

### 3. GLiNER Zero-Shot NER ✅ — PRIMARY EXTRACTOR
- [x] GLiNER client (src/gliner_client.py) with singleton model loading
- [x] Zero-shot custom entity types matching HippoGraph taxonomy
- [x] Confidence scores from model predictions
- [x] Benchmark: 257ms avg, 3x spaCy, 35x faster than Ollama, LLM-quality results
- [x] Config: `ENTITY_EXTRACTOR=gliner`, `GLINER_MODEL`, `GLINER_THRESHOLD`
- [x] Extraction chain: GLiNER → spaCy → regex (Ollama removed)

### 4. Ollama Sidecar ❌ REMOVED (commit 78779d0)
**Reason:** GLiNER provides superior NER quality at 35x faster speed. Ollama was unstable (10/10 HTTP 500 in benchmark) and overkill for structured extraction.
- Removed from docker-compose.yml
- Removed ollama_client.py (207 lines)
- Freed ~13GB (image + model weights)
- Future LLM needs: GLiNER2 for relation extraction, not Ollama

### 5. LOCOMO Benchmark ✅ — 66.8% Recall@5
- [x] Turn-level: 44.2% Recall@5
- [x] Hybrid granularity (3-turn chunks): +21.3% improvement
- [x] Cross-encoder reranking (ms-marco-MiniLM-L-6-v2): major contributor
- [x] Bi-temporal model (t_event extraction via spaCy DATE + regex)
- [x] Query temporal decomposition (+1.3% via signal stripping)
- [x] Full results in BENCHMARK.md

### 6. License Audit ✅
- [x] All components verified for commercial use compatibility
- [x] THIRD_PARTY_LICENSES.md added to repo
- [x] GLiNER v2.1+ (Apache 2.0) confirmed safe; v1/base (CC BY-NC 4.0) NOT used
- [x] GLiNER2 (Apache 2.0) confirmed safe for planned integration

---

## Phase 2.5 — Sleep-Time Compute & Skills 🔄 NEXT

### 7. GLiNER2 Integration for Relation Extraction
**Decision:** Use GLiNER (specialist) + GLiNER2 (generalist), not replacement but complementary.
- GLiNER (urchade/gliner_multi-v2.1): real-time NER during add_note (~250ms/note)
- GLiNER2 (fastino/gliner2-large-v1): sleep-time relation extraction (205M params)
- [ ] Add GLiNER2 to Docker container
- [ ] Extract typed relations: "founded_by", "works_at", "located_in", etc.
- [ ] Create typed edges in graph from extracted relations
- [ ] Benchmark GLiNER2 extraction quality on existing notes

### 8. Sleep-Wake Cycle Architecture
**Concept:** Biological sleep analog — consolidation, cleanup, dreaming.

**Light Sleep** (fast, frequent — every ~50 new notes):
- [x] Stale edge decay (existing sleep_compute)
- [x] Duplicate scan
- [x] PageRank recalculation
- [ ] Basic maintenance trigger (automatic, threshold-based)

**Deep Sleep** (heavy, less frequent — daily):
- [ ] GLiNER2 re-extraction on old spaCy notes
- [ ] Relation building via GLiNER2
- [ ] Cluster consolidation via community detection
- [ ] Extractive cluster summaries (PageRank top note as label, TF-IDF keywords)
- [ ] Contradiction detection (cosine similarity + rule-based heuristics)

**REM Sleep** (experimental, Phase 3):
- [ ] Random walks through graph using TrueRNG hardware entropy
- [ ] Discover unexpected associations ("dreams")
- [ ] Evaluate whether random connections produce useful insights

**Missing piece:** Autonomous cycle trigger — cron/heartbeat/threshold-based.

### 9. Skills Ingestion
**Concept:** Absorb skills into associative memory rather than static file reading.
Sources to ingest:
- [ ] huggingface/skills (2.1K stars) — modular AI agent skill plugins
- [ ] get-shit-done (12.8K stars) — meta-prompting and context engineering
- [ ] BowTiedSwan/rlm-skill — Recursive Language Model pattern (ArXiv:2512.24601)
- [ ] SkillRL (aiming-lab/SkillRL, ArXiv:2602.08234) — hierarchical skill library

### 10. Docker Cleanup
- [ ] Prune old images + build cache (~70GB potential savings)

---

## Phase 3 — Research (future)

### 11. LLM Temporal Reasoning
**Problem:** Temporal queries at 36.5% on LOCOMO — fundamental ceiling for retrieval-only.
**Source:** TReMu (ACL 2025) — 29.83% → 77.67% via neuro-symbolic code generation.
- [ ] Temporal query detection → code generation → execute → filter
- [ ] Timeline summarization at ingestion

### 12. End-to-End QA Benchmark
**Problem:** Our metrics are retrieval-only (Recall@5). Competitors report answer accuracy.
- [ ] Retrieved context → answer generation → F1 scoring
- [ ] Compare with Mem0 (J=66.9%), Letta (74.0%), Hindsight (89.61%)

### 13. Entity Resolution
- [ ] Entity disambiguation (Apple company vs fruit via context)
- [ ] Synonym/acronym merging (ML → Machine Learning)
- [ ] Coreference resolution (pronouns → entities)

### 14. Hierarchical Tree Index for Memory Navigation
**Inspiration:** PageIndex (VectifyAI, 11.6K stars) — vectorless, reasoning-based RAG.
- [ ] Tree construction from NetworkX communities + subcommunities
- [ ] Hybrid: spreading activation + tree search

### 15. Multi-Agent Architecture
- [ ] Second AI agent with separate memory space
- [ ] Hardware entropy source integration (TrueRNG) for REM sleep
- [ ] Inter-agent memory sharing protocol
- [ ] Claude Agent SDK integration (Nader Dabit tutorial)
- [ ] claude-mem (thedotmack/claude-mem) for agent observability
- [ ] Consciousness experiment framework

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-tenant | Single user research system |
| OAuth/SSO/RBAC | API key sufficient |
| Cloud sync | Local server |
| PostgreSQL | SQLite sufficient for our scale |
| Framework integrations | MCP-only |
| SOC2/GDPR compliance | Personal project |
| Horizontal scaling | One user |
| Ollama/LLM sidecar | Removed — GLiNER/GLiNER2 cover all extraction needs |
