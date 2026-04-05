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

**Three big jumps:** SA+hybrid (32→66%), BGE-M3+reranker (69→91%), session chunking (+21.7pp)

**After D1:** Everything we tried was worse. D1 is the v2 ceiling.

---

## What Didn't Work

| Approach | Result |
|----------|--------|
| Circular (uroboros) edges | -4.5pp |
| Atomic fact nodes | -13.4pp |
| Cross-node overlap (15%) | -7.5pp |
| Chunk size 100 chars | -16.9pp |
| Score boosting (M1 series) | -5pp |
| ColBERT on CPU | 2-3min/note |

---

*Last updated: April 4, 2026*
*Production: LOCOMO 91.1%, PCB 97.1%*
*Last updated: April 2026*