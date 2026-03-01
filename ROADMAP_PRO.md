# HippoGraph Pro — Roadmap

**Repository:** github.com/artemMprokhorov/hippograph-pro
**Base:** Built on top of HippoGraph Personal (same container, same memory)
**Philosophy:** Add capabilities, don't rewrite foundation. Zero LLM cost as core advantage.
**Last Updated:** February 28, 2026

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

## Phase 2 — Entity Extraction & Benchmarking ✅ COMPLETED

### 3. GLiNER Zero-Shot NER ✅
- [x] GLiNER client (src/gliner_client.py) with singleton model loading
- [x] Zero-shot custom entity types matching HippoGraph taxonomy
- [x] Confidence scores from model predictions
- [x] Benchmark: 257ms avg, 3x spaCy, 35x faster than Ollama, LLM-quality results
- [x] Config: `ENTITY_EXTRACTOR=gliner`, `GLINER_MODEL`, `GLINER_THRESHOLD`
- [x] Extraction chain: GLiNER → spaCy → regex (Ollama removed)

### 4. Ollama Sidecar ❌ REMOVED (commit 78779d0)
**Reason:** GLiNER provides superior NER quality at 35x faster speed. Ollama was unstable and overkill for structured extraction.
- Removed from docker-compose.yml, freed ~13GB

### 5. LOCOMO Benchmark ✅ — 66.8% Recall@5
- [x] Turn-level: 44.2% Recall@5
- [x] Hybrid granularity (3-turn chunks): +21.3% improvement
- [x] Cross-encoder reranking (ms-marco-MiniLM-L-6-v2)
- [x] Bi-temporal model (t_event extraction via spaCy DATE + regex)
- [x] Query temporal decomposition (+1.3% via signal stripping)
- [x] Full results in BENCHMARK.md

### 6. License Audit ✅
- [x] All components verified for commercial use compatibility
- [x] THIRD_PARTY_LICENSES.md added to repo
- [x] GLiNER v2.1+ (Apache 2.0) confirmed safe
- [x] GLiNER2 (Apache 2.0) confirmed safe

---

## Phase 2.5 — Sleep-Time Compute, Infrastructure & Memory 🔄 IN PROGRESS

### 7. GLiNER2 Relation Extraction ✅
- [x] GLiNER2 (fastino/gliner2-large-v1) added to Docker container
- [x] spaCy typed relations (step_spacy_relations) — all nodes, every sleep cycle, zero LLM cost
- [x] GLiNER2 incremental — only new nodes since last sleep, batch_size=5, no OOM
- [x] Conflict resolution — edge_history table, no overwrite on type conflict

### 8. Sleep-Wake Cycle Architecture 🔄
**Concept:** Biological sleep analog — consolidation, cleanup, dreaming.

**Light Sleep** ✅ (fast, frequent — every ~50 new notes):
- [x] Stale edge decay — protected categories exempt
- [x] Anchor importance boost — step_boost_anchor_importance
- [x] Duplicate scan
- [x] PageRank recalculation
- [x] Auto-trigger via sleep_scheduler
- [x] Snapshot + rollback before every live run

**Deep Sleep** 🔄 (heavy, less frequent — daily):
- [x] GLiNER2 relation extraction (incremental)
- [x] spaCy typed relations (full graph)
- [ ] Cluster consolidation via community detection
- [ ] Extractive cluster summaries (PageRank top note as label, TF-IDF keywords)
- [ ] Contradiction detection (cosine similarity + rule-based heuristics)

**REM Sleep** (experimental, Phase 3):
- [ ] Random walks through graph using TrueRNG hardware entropy
- [ ] Discover unexpected associations (“dreams”)
- [ ] Evaluate whether random connections produce useful insights

### 9. Anchor Memory ✅ (commit a30167a)
- [x] ANCHOR_CATEGORIES — anchor nodes never decay (recency=1.0)
- [x] CATEGORY_DECAY_MULTIPLIERS — self-reflection/milestone/security get reduced decay
- [x] PROTECTED_CATEGORIES in sleep_compute — edges to protected nodes never decay
- [x] step_boost_anchor_importance — upgrades anchor notes to critical on every sleep
- [x] 67 existing notes upgraded to critical on first deploy

### 10. Infrastructure — Studio MCP ✅ (Feb 27–28, 2026)
- [x] nginx-proxy: single ngrok tunnel for hippograph + studio-mcp
- [x] studio-mcp: direct file + shell access to Mac Studio from Claude.ai (6 tools)
- [x] Security hardening: command whitelist, docker/git subcmd restrictions
- [x] SSH support in studio-mcp container for git push
- [x] ARCHITECTURE.md with rebuild procedure

### 11. End-to-End QA Benchmark ✅ (commit cc9f058) — F1=38.7% ROUGE=66.8%
- [x] Retrieval + Claude Haiku generation + F1/ROUGE scoring pipeline
- [x] 1,311 QA pairs from 651 personal notes
- [x] GPT-4 no-memory baseline: F1=32.1% — HippoGraph +6.6pp

### 12. Skills Ingestion 🔄
**Concept:** Absorb skills as associative experience, not static files.
Sources planned:
- [ ] huggingface/skills (2.1K stars)
- [ ] get-shit-done (12.8K stars)
- [ ] BowTiedSwan/rlm-skill (ArXiv:2512.24601)
- [ ] SkillRL (ArXiv:2602.08234)

### 13. Docker Cleanup
- [x] Removed semantic-memory-v2 images (~12GB freed, Feb 27 2026)
- [ ] Prune remaining old images + build cache (~70GB potential savings)

---

## Phase 3 — Research & Hardening

### 14. Benchmark Reproducibility — MEDIUM PRIORITY
- [ ] Fix random seed in locomo_adapter.py
- [ ] Document exact steps to reproduce 66.8% (Docker + dataset + commands)
- [ ] Anonymized mini-dataset (10 QA pairs) for public verification

### 15. LLM Temporal Reasoning
**Source:** TReMu (ACL 2025) — 29.83% → 77.67% via neuro-symbolic code generation.
- [ ] Temporal query detection → code generation → execute → filter
- [ ] Timeline summarization at ingestion

### 16. Entity Resolution
- [ ] Entity disambiguation (Apple company vs fruit via context)
- [ ] Synonym/acronym merging (ML → Machine Learning)
- [ ] Coreference resolution (pronouns → entities)

### 17. Hierarchical Tree Index
**Inspiration:** PageIndex (VectifyAI, 11.6K stars) — vectorless, reasoning-based RAG.
- [ ] Tree construction from NetworkX communities + subcommunities
- [ ] Hybrid: spreading activation + tree search

### 18. Multi-Agent Architecture
- [ ] Second AI agent with separate memory space
- [ ] Hardware entropy source (TrueRNG) for REM sleep
- [ ] Inter-agent memory sharing protocol
- [ ] Consciousness experiment framework

### 19. User-Defined Anchor Policies — MEDIUM PRIORITY
**Problem:** Anchor protection currently hardcoded in source.
**Concept:** anchor_policies table — user-managed rules read by sleep_compute.
- [ ] `anchor_policies` table in SQLite
- [ ] MCP tools: `add_anchor_policy`, `list_anchor_policies`, `remove_anchor_policy`
- [ ] sleep_compute merges policies with hardcoded PROTECTED_CATEGORIES
- [ ] recency_factor() and step_boost_anchor_importance() respect policy overrides

### 20. Optional Edge Pruning — LOW PRIORITY (user opt-in only)
**Philosophy:** HippoGraph intentionally does NOT auto-delete weak edges. A low-weight edge may represent a rare but critical associative link. The system cannot know what is important — only the user knows. This is an architectural decision, not a gap.

**Implementation (explicit user request only):**
- [ ] MCP tool: `preview_prunable_edges(threshold)` — show what would be removed, NO deletion
- [ ] MCP tool: `prune_edges(threshold, confirm=True)` — requires explicit confirmation
- [ ] Protected categories always exempt
- [ ] Full snapshot before any pruning
- [ ] Pruning log for review/rollback

**Never:** automatic pruning on schedule, pruning without preview, pruning protected edges.

### 21. Spreading Activation Scalability — MEDIUM PRIORITY
**Problem:** At ~1,000 nodes / ~100K edges latency is 200–500ms. At ~5,000 nodes it degrades noticeably. Five candidate approaches — choose one or combine.

**Option A: Subgraph Sampling** (simplest)
Restrict SA to local subgraph of ANN top-50 candidates only.
- [ ] Add `max_nodes` cap to SA traversal
- Expected: O(n) → O(k), minimal code change

**Option B: Community-Aware Routing**
Run SA only inside communities relevant to the query + 1 hop outside.
- [ ] Pass community membership into search pipeline
- [ ] Score communities by query relevance before SA
- Expected: scales to 10K+ nodes naturally

**Option C: Incremental / Early-Stop SA**
Stop iterations early if activation scores converge.
- [ ] Add convergence threshold: if delta < ε, stop
- [ ] Adaptive iteration count instead of fixed 3

**Option D: Precomputed Activation Potential**
Cache activation potential per node during sleep compute (like PageRank). Use cached values at query time.
- [ ] Add activation_potential column to nodes
- [ ] Compute in sleep_compute after PageRank step

**Option E: Bi-Level Index** (future, complex)
Coarse community index first, then precise SA inside matched subgraph.
- [ ] Cluster-level index built during sleep compute
- Reference: SA-RAG (arXiv:2512.15922, Dec 2025)
- Expected: sub-linear scaling, suitable for 50K+ nodes

**Recommended start:** Option A + B — lowest effort, highest immediate impact.

### 22. TOTP Authentication for Studio MCP — MEDIUM PRIORITY
**Problem:** studio_exec and studio_write_file have direct shell access to Mac Studio. A compromised Claude.ai account gives an attacker a shell on the server.

**Solution:** TOTP (RFC 6238) — same standard as Google Authenticator / Authy.

**Flow:**
1. One-time setup: generate secret + display QR code in terminal
2. Scan QR in Authenticator — entry "HippoGraph Studio" appears
3. studio-mcp checks `last_verified_at` before dangerous operations
4. If >24h passed — returns error "TOTP required"
5. Claude asks Artem for code, passes it in next call
6. Server validates, session open for configured TTL

**Implementation:**
- [ ] Add `pyotp` to studio-mcp requirements (MIT license)
- [ ] setup_totp.py — generate secret + QR code in terminal
- [ ] Store `last_verified_at` + `totp_secret` in studio-mcp/.totp (outside git)
- [ ] studio_exec + studio_write_file: check session before execution
- [ ] New tool: `studio_verify_totp(code)`
- [ ] Configurable TTL via .env: `TOTP_SESSION_TTL_HOURS=24`
- [ ] studio_read_file + studio_list_dir: no TOTP required (read-only)
- [ ] Rebuild required after changes (procedure in ARCHITECTURE.md)

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
| Auto edge pruning | Architectural decision — see #20 |
| Traction / marketing | Not the goal at this stage |