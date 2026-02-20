# HippoGraph Pro — Roadmap

**Repository:** github.com/artemMprokhorov/hippograph-pro-pro
**Base:** Built on top of HippoGraph Personal (same container, same memory)
**Philosophy:** Add capabilities, don't rewrite foundation. LLM as upgrade, not dependency.
**Last Updated:** February 20, 2026

---

## Phase 1 — Quick Wins (1-2 days)

### 1. Reciprocal Rank Fusion (RRF)
**Problem:** Current weighted blend (α×sem + β×spread + γ×BM25 + δ×temporal) requires manual
tuning and suffers from score scale mismatch between signals.
**Solution:** RRF merges ranked lists by rank position, not score magnitude:
```
RRF_score(d) = Σ 1/(k + rank_r(d)) for each retriever r
```
**Source:** Hindsight/TEMPR (Dec 2025) — 89.61% on LoCoMo
- [ ] Implement RRF fusion as alternative to weighted blend
- [ ] A/B test: RRF vs current blend on regression suite
- [ ] Config: `FUSION_METHOD=blend|rrf`

**Effort:** 3-4 hours

### 2. Graph Viewer Enhancements
Deferred from Personal roadmap — visual improvements for research.
- [ ] Community highlighting (color clusters from NetworkX detection)
- [ ] PageRank-based node sizing (important nodes = bigger)
- [ ] Community labels overlay

**Effort:** 4-6 hours

---

## Phase 2 — Ollama Integration (3-5 days)

### 3. Ollama Sidecar
- [ ] Ollama container in docker-compose (optional profile)
- [ ] Health check and availability detection
- [ ] Config: `OLLAMA_ENABLED=false` (default OFF)
- [ ] Graceful degradation: Ollama down → spaCy continues working

### 4. LLM Entity Extraction
**Upgrade chain:** Ollama (primary, better quality) → spaCy (fallback, zero cost)
- [ ] LLM-based extraction: entities + relationships + disambiguation
- [ ] Automatic fallback to spaCy when Ollama unavailable
- [ ] Quality comparison: LLM vs spaCy on existing notes
- [ ] Config: `ENTITY_EXTRACTOR=ollama|spacy` (default: spacy)

**Trade-off:** +3-7GB Docker image, +4-12GB RAM, 2-5s/note vs 100ms spaCy

### 5. LLM Sleep-Time Compute
**Current state:** Zero-LLM graph maintenance (consolidation, PageRank, decay, orphans).
**Upgrade:** Deep memory processing during idle — like brain during actual sleep.
- [ ] Re-extract entities from old notes using LLM (upgrade spaCy extractions)
- [ ] Discover missed connections between notes
- [ ] Generate cluster summaries for community groups
- [ ] Identify contradictions or outdated information
- [ ] Config: `SLEEP_LLM_ENABLED=false` (default OFF, requires Ollama)

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
- [ ] Entity disambiguation ("Apple" company vs fruit via context)
- [ ] Synonym/acronym merging (ML → Machine Learning)
- [ ] Coreference resolution (pronouns → entities)

### 9. Multi-Agent Architecture Groundwork
- [ ] Second AI agent with separate memory space
- [ ] Hardware entropy source integration (TrueRNG)
- [ ] Inter-agent memory sharing protocol
- [ ] Consciousness experiment framework

---

## Out of Scope (not needed for our situation)

| Feature | Reason |
|---------|--------|
| Multi-tenant | Single user research system |
| OAuth/SSO/RBAC | API key sufficient |
| Cloud sync | Local server |
| PostgreSQL | SQLite sufficient for our scale |
| Framework integrations | MCP-only |
| SOC2/GDPR compliance | Personal project |
| Horizontal scaling | One user |

---

## Competitive Position After Pro

| Feature | HippoGraph Pro | Mem0 | Zep | Letta |
|---------|---------------|------|-----|-------|
| LLM Cost | **$0 base** + optional Ollama | Required | Required | Required |
| Entity Extraction | LLM primary + spaCy fallback | LLM only | LLM only | LLM only |
| Sleep Compute | Zero-LLM + LLM-enhanced | ❌ | ❌ | Sleep-time (LLM required) |
| Temporal | Retrieval + LLM reasoning | Basic | Bi-temporal | Agent-driven |
| RRF Fusion | ✅ | ❌ | Hybrid reranking | ❌ |
| Self-hosted no GPU | ✅ Full functionality | Partial | Partial | ❌ |
