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
**Result:** +3.9pp LOCOMO. BGE-M3 (1024-dim, 8192 ctx, MIT) became production model.

---

## Retrieval Architecture

### Session vs Turn Granularity (February 2026)
**Result:** Turn-level: 44.2%. Session-level: 32.6%. Session + overlap chunking: 91.1%.

### BGE-M3 Sparse Mode (March 2026)
**Result:** Delta 0pp. BM25 already covers keyword matching.

### ColBERT Late Chunking (March 2026)
**Result:** 2-3 minutes per note on CPU. Unacceptable.

### Overlap Chunking D1 🏆 (March 31, 2026)
**Result:** **91.1% LOCOMO Recall@5** (+21.7pp). Production architecture.
- Session granularity + 50% intra-node overlap + parent nodes
- BGE-M3 + BM25 + Spreading Activation + bge-reranker-v2-m3

### E-Series: Parentless Chunking (April 1, 2026)
**Result:** E1 (parentless) = 89.7% — within 1.4pp of D1. Circular edges hurt (-4.5pp).
**What we learned:** Graph nearly replaces parent organically. SA doesn't understand chunk chains as reinforcing signal.

### H-Series: Keyword Anchors (April 5-6, 2026)
Keyword anchors are lightweight routing nodes capturing key entities from notes.

**Key finding:** Batch keyword anchors created AFTER sleep consolidation outperform inline anchors created at ingestion. When anchors are added to an established graph, they integrate better into the topology.

| Config | Overall | single-hop | multi-hop | temporal | open-domain |
|--------|---------|-----------|----------|---------|------------|
| D1 production | 91.1% | 85.5% | 89.1% | 66.7% | 96.6% |
| H1 (no atomic-facts) | 84.3% | — | — | — | — |
| H2 (sentence chunking) | 85.2% | 81.9% | 82.6% | 64.6% | 89.7% |
| H4 (inline anchors) | 88.3% | 84.8% | 85.7% | 61.5% | 93.6% |
| **H3 (batch anchors)** | **90.8%** | **91.5%** | **90.3%** | 65.6% | 93.6% |

**H3 single-hop 91.5% exceeds D1 (85.5%)!**

**Implementation:** Add keyword anchor step to sleep_compute.py AFTER consolidation, BEFORE temporal/entity edge building.

### M4: Chunk-Aware Inhibition (April 9, 2026)
Within a chunk ring (lc-chunks from the same parent), the winner takes more — other chunks in the ring are suppressed with higher strength (CHUNK_INHIBITION_STRENGTH=0.6).

**Hypothesis:** Reduces intra-note noise in top-K, improves diversity.

| Config | Overall | single-hop | multi-hop | temporal | open-domain |
|--------|---------|-----------|----------|---------|------------|
| H3 baseline | 90.8% | 91.5% | 90.3% | 65.6% | 93.6% |
| M4 | 89.1% | 91.5% | 88.2% | 65.6% | 91.4% |

**Result:** -1.7pp overall. single-hop and temporal held, multi-hop and open-domain regressed.

**What went wrong:** Chunk inhibition suppresses chunks when the correct answer is *distributed* across multiple chunks of the same note — exactly the multi-hop and open-domain patterns. The inhibition that was meant to reduce noise instead cut signal.

**Status:** Kept in production (PCB unaffected), but not a LOCOMO improvement.

### M5: Chunk-Aware Consolidation (April 9, 2026)
Sleep builds consolidation edges only *between* chunk rings from different sessions, skipping edges *within* the same ring. Hypothesis: intra-ring edges are noise, inter-ring edges carry signal.

**Result:** ~91.1% on 1286/1540 queries before server reboot — slightly above H3. Full result pending rerun.

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

## LOCOMO Recall@5 — Key Results

| Date | Config | Recall@5 |
|------|--------|----------|
| Feb 2026 | Session baseline | 32.6% |
| Feb 2026 | Turn-level MiniLM | 44.2% |
| Mar 7 | hippograph-pro | 66.6% |
| Mar 28 | BGE-M3 rebuild | 69.4% |
| Mar 31 | **D1 Production** | **91.1%** |
| Apr 1 | E1 parentless | 89.7% |
| Apr 2 | M1 variants | 86.0-86.4% |
| Apr 3 | M2/G cross-node overlap | 74.2-83.6% |
| Apr 6 | H3 batch keyword anchors | **90.8%** |
| Apr 9 | M4 chunk-aware inhibition | 89.1% |
| Apr 9 | M5 chunk-aware consolidation | ~91.1% (partial) |

**Three big jumps:** SA+hybrid (32→66%), BGE-M3+reranker (69→91%), session chunking (+21.7pp)

---

## Open Issues

### Temporal Category — Persistent Bottleneck
Temporal questions score ~65% across ALL experiments. Keyword anchors don't help — they're semantic, not temporal. Requires dedicated temporal scoring experiment.

---

## What Didn't Work

| Approach | Result |
|----------|--------|
| Circular (uroboros) edges | -4.5pp |
| Atomic fact nodes (separate) | -13.4pp |
| Cross-node overlap (15%) | -7.5pp |
| Chunk size 100 chars | -16.9pp |
| Score boosting (M1 series) | -5pp |
| ColBERT on CPU | 2-3min/note |
| spaCy sentencizer chunking | -5.9pp vs D1 |
| Inline keyword anchors | -2.8pp vs batch |
| Chunk-aware inhibition (M4) | -1.7pp overall |

---

*Last updated: April 9, 2026*
*Production: LOCOMO 90.8% (H3), PCB 97.5%*
*Best experimental result: H3 single-hop 91.5%*