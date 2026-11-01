# HippoGraph Pro — Experiments Log

This document records the full research journey from HippoGraph Pro.

**Philosophy:** "What didn't work" is as valuable as "what worked."

---

## Infrastructure & Embeddings

### ChromaDB as Vector Store (Early 2025)
**Result:** Too slow. Moved to local SQLite + HNSWlib.

### sentence-transformers on ARM64 (Early 2025)
**Result:** Segfault on M3 Ultra. Switched to direct HuggingFace transformers.

### OpenAI Embeddings API (Early 2025)
**Result:** Vendor lock-in + cost. Moved to fully local models.

### Ollama for NER (2025)
**Result:** 35x slower than GLiNER. Removed entirely.

### MiniLM-384 → BGE-M3 (2025 → March 2026)
**Result:** Improvement on LOCOMO. BGE-M3 (1024-dim, 8192 ctx, MIT) became production model.

---

## Retrieval Architecture

### Session vs Turn Granularity (February 2026)
**Result:** Turn-level outperforms session-level; session + overlap chunking outperforms both.

### BGE-M3 Sparse Mode (March 2026)
**Result:** No gain. BM25 already covers keyword matching.

### ColBERT Late Chunking (March 2026)
**Result:** 2-3 minutes per note on CPU. Unacceptable.

### Overlap Chunking D1 🏆 (March 31, 2026)
**Result:** Best LOCOMO configuration. Production architecture.
- Session granularity + 50% intra-node overlap + parent nodes
- BGE-M3 + BM25 + Spreading Activation + bge-reranker-v2-m3

### E-Series: Parentless Chunking (April 1, 2026)
**Result:** E1 (parentless) comes close to D1. Circular edges hurt.
**What we learned:** Graph nearly replaces parent organically. SA doesn't understand chunk chains as reinforcing signal.

### H-Series: Keyword Anchors (April 5-6, 2026)
Keyword anchors are lightweight routing nodes capturing key entities from notes.

**Key finding:** Batch keyword anchors created AFTER sleep consolidation outperform inline anchors created at ingestion. When anchors are added to an established graph, they integrate better into the topology.

| Config |
|--------|
| D1 production |
| H1 (no atomic-facts) |
| H2 (sentence chunking) |
| H4 (inline anchors) |
| **H3 (batch anchors)** |

**H3 single-hop exceeds D1!**

**Implementation:** Add keyword anchor step to sleep_compute.py AFTER consolidation, BEFORE temporal/entity edge building.

### M4: Chunk-Aware Inhibition (April 9, 2026)
Within a chunk ring (lc-chunks from the same parent), the winner takes more — other chunks in the ring are suppressed with higher strength (CHUNK_INHIBITION_STRENGTH=0.6).

**Hypothesis:** Reduces intra-note noise in top-K, improves diversity.

**Result:** Overall regression vs H3 baseline. Single-hop and temporal held, multi-hop and open-domain regressed.

**What went wrong:** Chunk inhibition suppresses chunks when the correct answer is *distributed* across multiple chunks of the same note — exactly the multi-hop and open-domain patterns. The inhibition that was meant to reduce noise instead cut signal.

**Status:** Kept in production (PCB unaffected), but not a LOCOMO improvement.

### M5: Chunk-Aware Consolidation (April 9, 2026)
Sleep builds consolidation edges only *between* chunk rings from different sessions, skipping edges *within* the same ring. Hypothesis: intra-ring edges are noise, inter-ring edges carry signal.

**Result:** Partial run (1286/1540 queries) before server reboot — slightly above H3. Full result pending rerun.

**Status:** Promising, needs clean completion.

---

## sleep_compute Idempotency Bug (April 2026)

**Discovered by:** community contributor (sm1ly, PR #2)

**Bug:** `sleep_compute` was not idempotent — each run created new abstract-topic nodes and edges on top of previous ones. Root causes:
1. k-means counted synthetic nodes (abstract-topic, lc-chunk, metrics-snapshot) when computing cluster count k, inflating it each run
2. Old BELONGS_TO edges not cleaned before re-clustering — tfidf and kmeans steps conflicted
3. metrics-snapshot nodes categorized as `milestone` (anchor-protected), pulling them into k-means

**Impact:** 2844 duplicate abstract-topic nodes accumulated in production before fix.

**Fix:**
- Clean old abstract-topic nodes and edges before re-clustering (idempotent re-run)
- Exclude synthetic categories from k-means embedding pool
- Change metrics-snapshot category from `milestone` to `metrics-snapshot` (not anchor-protected)
- Remove `step_topic_linking_tfidf` from pipeline (kmeans subsumes it)

**Lesson:** Sleep compute must be designed as an idempotent operation from the start. Any step that creates nodes must first clean its previous outputs.

---

## Prospective Memory (April 9, 2026)

**Concept:** A distinct category of notes for future intentions — plans, tasks, reminders — with decay protection while pending and automatic decay resumption after completion.

**Implementation:**
- Category `prospective`, tags: `pending` / `done` / `cancelled`
- `pending` → `importance=critical` (anchor-protected, no decay)
- `done` / `cancelled` → `importance=low` (normal decay resumes)
- `PROSPECTIVE_BOOST=0.20` — pending notes get activation boost in spreading activation, surfacing even for loosely related queries
- Optional `due:YYYY-MM-DD` tag → auto-marked `[OVERDUE]` after due date
- Processed in sleep via `step_prospective_memory()`
- CLI: `--add-intention`, `--complete-intention`, `--list-intentions`
- MCP tools: `add_intention()`, `complete_intention()`

**What we learned:** The graph naturally handles episodic (past) memory well. Prospective (future) memory requires explicit protection from decay — without it, pending intentions fade like any other note. The boost ensures plans surface proactively rather than only when explicitly searched.

---

## LOCOMO — Key Configurations

| Date | Config |
|------|--------|
| Feb 2026 | Session baseline |
| Feb 2026 | Turn-level MiniLM |
| Mar 7 | hippograph-pro |
| Mar 28 | BGE-M3 rebuild |
| Mar 31 | **D1 Production** |
| Apr 1 | E1 parentless |
| Apr 2 | M1 variants |
| Apr 3 | M2/G cross-node overlap |
| Apr 6 | H3 batch keyword anchors |
| Apr 9 | M4 chunk-aware inhibition |
| Apr 9 | M5 chunk-aware consolidation (partial) |

**Three big jumps:** SA+hybrid, BGE-M3+reranker, session chunking

---

## Open Issues

### Temporal Category — Persistent Bottleneck
Temporal questions plateau at the same level across ALL experiments. Keyword anchors don't help — they're semantic, not temporal. Requires dedicated temporal scoring experiment.

---

## What Didn't Work

| Approach | Result |
|----------|--------|
| Circular (uroboros) edges | — |
| Atomic fact nodes (separate) | — |
| Cross-node overlap (15%) | — |
| Chunk size 100 chars | — |
| Score boosting (M1 series) | — |
| ColBERT on CPU | 2-3min/note |
| spaCy sentencizer chunking | — |
| Inline keyword anchors | — |
| Chunk-aware inhibition (M4) | — |

---

*Last updated: April 9, 2026*
*Production: H3 config, PCB 97.5%*
*Best experimental result: H3 single-hop*