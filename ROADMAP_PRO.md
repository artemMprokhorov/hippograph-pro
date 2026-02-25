# HippoGraph Pro — Roadmap

**Repository:** github.com/artemMprokhorov/hippograph-pro
**Base:** Built on top of HippoGraph Personal (same container, same memory)
**Philosophy:** Add capabilities, don't rewrite foundation. LLM as upgrade, not dependency.
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

## Phase 2 — Entity Extraction & LLM Integration ✅ MOSTLY COMPLETE

### 3. GLiNER Zero-Shot NER ✅ NEW — PRIMARY EXTRACTOR
- [x] GLiNER client (src/gliner_client.py) with singleton model loading
- [x] Zero-shot custom entity types matching HippoGraph taxonomy
- [x] Confidence scores from model predictions
- [x] Benchmark: 257ms avg, 3x spaCy, 35x faster than Ollama, LLM-quality results
- [x] Config: `ENTITY_EXTRACTOR=gliner`, `GLINER_MODEL`, `GLINER_THRESHOLD`

### 4. Ollama Sidecar ✅
- [x] Ollama container in docker-compose (optional profile)
- [x] Health check and availability detection
- [x] Graceful degradation: Ollama down → GLiNER → spaCy continues working
- [x] Config: `OLLAMA_MODEL=qwen2.5:7b` (user-configurable)

### 5. LLM Entity Extraction ✅ (SUPERSEDED BY GLiNER FOR NER)
**Original plan:** Ollama as primary NER. **Revised:** GLiNER is better for NER (faster, more stable).
**Ollama role changed:** Generation tasks only (summaries, sleep-time analysis, temporal reasoning).
- [x] LLM-based extraction implemented and benchmarked
- [x] Quality comparison: Ollama 30x slower than spaCy, GLiNER 3x slower with same quality
- [x] Extraction chain: GLiNER → Ollama → spaCy → regex
- [x] Config: `ENTITY_EXTRACTOR=gliner|ollama|spacy|regex`

### 6. LLM Sleep-Time Compute 🔄 IN PROGRESS
**Current state:** Zero-LLM graph maintenance (consolidation, PageRank, decay, orphans).
**Upgrade:** Deep memory processing during idle — like brain during actual sleep.
- [ ] Re-extract entities from old notes using GLiNER (upgrade spaCy extractions)
- [ ] Discover missed connections between notes
- [ ] Generate cluster summaries for community groups (Ollama)
- [ ] Identify contradictions or outdated information (Ollama)
- [ ] Config: `SLEEP_LLM_ENABLED=false` (default OFF)

---

## Phase 3 — Research (ongoing)

### 6. LLM Temporal Reasoning
**Problem:** Temporal queries at 36.5% on LOCOMO — fundamental ceiling for retrieval-only.
**Source:** TReMu (ACL 2025) — 29.83% → 77.67% via neuro-symbolic code generation.
- [ ] Temporal query detection → LLM code generation → execute → filter
- [ ] Timeline summarization at ingestion
- [ ] Graceful degradation without Ollama

### 7. End-to-End QA Benchmark
**Problem:** Our metrics are retrieval-only (Recall@5). Competitors report answer accuracy.
- [ ] Retrieved context → Ollama answer generation → F1 scoring
- [ ] Compare with Mem0 (J=66.9%), Letta (74.0%), Hindsight (89.61%)

### 8. Entity Resolution
- [ ] Entity disambiguation (Apple company vs fruit via context)
- [ ] Synonym/acronym merging (ML → Machine Learning)
- [ ] Coreference resolution (pronouns → entities)

### 9. Hierarchical Tree Index for Memory Navigation
**Inspiration:** PageIndex (VectifyAI, 11.6K stars) — vectorless, reasoning-based RAG via hierarchical tree search.
**Idea:** Build a tree structure from community detection: Topics → Subtopics → Individual notes.
Enables top-down navigation ("narrow the theme, then dive deep") as complement to our bottom-up spreading activation.
- [ ] Research: tree construction from NetworkX communities + subcommunities
- [ ] Tree search as alternative retrieval path (LLM reasons over tree vs activation spreading)
- [ ] Hybrid: spreading activation for associative recall, tree search for structured exploration
- [ ] Evaluate when memory grows to 1000+ notes and activation becomes too broad

**Key insight:** "similarity ≠ relevance" — both PageIndex and HippoGraph address this, but differently. They use LLM reasoning over structure, we use biologically-inspired activation. Combining both could be powerful.

### 10. Multi-Agent Architecture Groundwork
- [ ] Second AI agent with separate memory space
- [ ] Hardware entropy source integration (TrueRNG)
- [ ] Inter-agent memory sharing protocol
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
