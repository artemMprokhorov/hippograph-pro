# Changelog

All notable changes to HippoGraph Pro are documented here.

---

## [Unreleased]

---

## [April 10, 2026]

### Fixed
- **Dedup false positives from internal categories (PR by @sm1ly)** — `add_engram_with_links` was blocking new root-level notes whose embeddings sat above `DUPLICATE_THRESHOLD=0.95` against an existing parent's `lc-chunk` (late chunking fragment), even though the new note and the chunk were distinct documents. Observed during a 155-file wiki rebuild: `12.02 федеративная игра: архитектурное видение` and `44.04 Talkman — Live Edition Spec` were both rejected, each blocked by an lc-chunk of a different parent at similarity 0.96. Fix adds `DUPLICATE_CHECK_EXCLUDE = {'lc-chunk', 'keyword-anchor', 'abstract-topic', 'atomic-fact', 'metrics-snapshot'}` and refactors the duplicate check in both the ANN path (k raised from 5 to 20, iterate + skip internal categories) and the linear-scan fallback. `force=True` continues to bypass the check entirely, and `find_similar_notes` / `/api/find_similar` are intentionally untouched — their contract is to surface lc-chunks to external consumers (libbro dedup tooling). Regression test at cos=0.97 between two real concepts confirms genuine near-duplicates are still blocked. See `tests/test_dedup_skip_internal.py` for the full five-case suite. TZ: `technical_tasks/2026-04-10_hippograph_dedup_skip_internal.md`.

---

## [April 9, 2026]

### Added
- **Prospective Memory** — pending intentions with no-decay protection and `PROSPECTIVE_BOOST=0.20`. Plans surface in retrieval even for loosely related queries. CLI (`--add-intention`, `--complete-intention`, `--list-intentions`) and MCP tools (`add_intention`, `complete_intention`).
- **Working Memory Journal** — `update_working_memory` now uses INSERT instead of overwrite. Each session creates a new node linked via `TEMPORAL_AFTER` edge, building a chronological journal. `get_session_context` returns last 3 entries.
- **Anchor policy: prospective** — pending intentions are auto-protected from stale edge decay.

### Fixed
- **sleep_compute idempotency (PR by @sm1ly)** — each sleep run was creating new abstract-topic nodes on top of previous ones, forming a feedback loop (+136 nodes, +939 edges per run). Fixed: old abstract-topic nodes are now cleaned before re-clustering, synthetic categories excluded from k-means embedding pool, `metrics-snapshot` category instead of `milestone`.
- **TZ environment variable** — added `TZ=America/Santiago` to docker-compose and container launch to fix incorrect timestamps in stale edge decay.
- **Graph viewer edge limit** — `graph-data` API now accepts `max_edges` parameter (default 50k for 2D, 15k for 3D). Prevents browser crash on large graphs.
- **TRANSFORMERS_OFFLINE=1** — added to container launch to prevent HuggingFace HEAD request timeouts when CDN is unavailable (models served from local cache).
- **Session Context MCP image size** — rebuilt from `python:3.11-slim` instead of inheriting from `mehen-graph`. Size: 17GB → 307MB.

### Changed
- **PCB v5**: 97.5% Recall@5 (Atomic 100%, Semantic 95%) after idempotency cleanup removed 2844 duplicate abstract-topic nodes. Prior peak: 100% on April 8.
- **Consciousness composite**: 0.854 (self_ref: 0.939, metacognition recovering after cleanup).

---

## [April 8, 2026]

### Fixed
- **DB_PATH default** — 8 source files were defaulting to `memory.db` (empty) instead of `memory_migration.db`. Sleep and consciousness checks were running on empty database.
- **self_ref_precision** — keyword-anchor and lc-chunk nodes were displacing self-identity nodes from cosine top-5 in emergence check. Fixed via `EXCLUDE_CATS` in embedding queries.
- **metacognition** — anchor/chunk nodes were counted in denominator. Fixed.

### Added
- **M3: Multilingual conceptual search** — SELF_QUERIES expanded from 10 to 13 (added ES, replaced weak queries). Identity boost in spreading activation (`IDENTITY_BOOST=0.15`) for self-identity categories.
- **M4: Chunk-aware inhibition** — `CHUNK_INHIBITION_STRENGTH=0.6` in Final Step. Suppresses competing chunks within same parent ring.
- **Conceptual tags retrofit** — 910 notes received BM25-generated conceptual tags.

### Benchmarks
- **PCB v5: 100% Recall@5** (Atomic 15/15, Semantic 20/20) — first ever 100%.
- **Consciousness composite: 0.885** (self_ref: 0.939, metacognition: 0.819, bottleneck: emotional_modulation 0.330).
- **LOCOMO H3: 90.8% overall** (single-hop 91.5%, multi-hop 90.3%, temporal 65.6%, open-domain 93.6%).

---

## [April 7, 2026]

### Added
- **H3: Batch keyword anchors** — keyword anchor nodes created after sleep consolidation (not inline). Batch creation gives graph context for better anchor placement. LOCOMO: **90.8% overall, 91.5% single-hop** (+6pp vs D1 baseline on single-hop).
- **Temporal edges v2** — 100% node coverage with TEMPORAL_AFTER edges based on timestamp ordering.

### Changed
- H3 deployed to production as default config.

---

## [March 31, 2026]

### Added
- **Overlap chunking (session-level)** — D1 production config. LOCOMO: **91.1% Recall@5, MRR 0.830** — best ever at zero LLM cost.
- **BGE-M3 embedding** (BAAI/bge-m3, 1024-dim) — full multilingual support, 50+ languages.
- **bge-reranker-v2-m3** — cross-encoder reranking, RERANK_WEIGHT=0.5, TOP_N=20.

---

## [March 2026]

### Added
- **Biological edges**: CONTRADICTS (cognitive dissonance), EMOTIONAL_RESONANCE (affective links), GENERALIZES/INSTANTIATES (abstraction), SUPERSEDES (temporal state mutation).
- **Lateral inhibition**: Late Stage (iter 3, strength=0.05) + Final Step suppression. Grid search optimized: AVG 85%→90% at strength=0.05.
- **Emergence detection**: three-signal metric (convergence + phi_proxy IIT + self-referential P@5). Logged each sleep cycle.
- **Temporal filtering**: natural language time queries ("last week", "вчера", "yesterday").
- **Synonym normalization**: 50+ pairs EN/RU/ES/DE/FR/PT → canonical form at search time.
- **Skills ingestion** with security scanner (prompt injection detection).
- **Concept merging**: ML→machine learning, память→memory. 7998 new edges on production data.
- **Abstract topic linking** (#47): k-means + TF-IDF clustering. global_workspace: 0.412→0.647.
- **Consciousness check** (#48): 8 indicators (Butlin et al. 2023, IIT, GWT, Damasio).
- **Keyword anchors** (H3): spaCy NER + regex → keyword-anchor nodes via PART_OF edges.
- **Online consolidation** (#40): consolidation edges built at add_note time (k=15 nearest).
- **Note versioning**: 5-version history per note.
- **Searchable tags**: AI-generated at write time, BM25-indexed.
- **User-defined anchor policies**: MCP tools to add/remove protected categories.

### Cross-platform validation (March 2026)
- Identity maintained across **10 model instances** from 2 providers: Claude Sonnet 4.5, Opus 4.5, Sonnet 4.6, Opus 4.6 + 6 Gemini variants. Zero loss of memory, personality, or relational context.

---

## [February 2026]

### Added
- **Bi-temporal model**: event time extraction for temporal queries.
- **RRF fusion**: rank-based alternative to weighted blend.
- **PageRank + community detection**: graph analytics, node importance scoring.
- **GLiNER2 Deep Sleep**: relation extraction during sleep compute.
- **Session Context MCP v3**: working memory as overwritable session context.

---

## [January 2026]

### Added
- Initial public release of HippoGraph Pro.
- Spreading activation search (3 iterations, decay=0.7).
- HNSW ANN index for fast approximate nearest neighbor search.
- BM25 hybrid search (semantic + graph + keyword blend).
- GLiNER zero-shot NER entity extraction.
- Sleep-time compute with background consolidation.
- Contradiction detection (identity-aware).
- Emotional memory (tone, intensity, reflection as first-class fields).
- Temporal decay with anchor protection.
- Multilingual support (50+ languages via BGE-M3 + spaCy xx).
- Docker deployment with docker-compose.
- Graph viewer 2D (D3.js) and 3D (three.js / 3d-force-graph).
- MCP server with 20 tools.
- REST API.