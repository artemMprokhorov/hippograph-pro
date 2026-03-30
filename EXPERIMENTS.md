# HippoGraph Pro — Experiments Log

This document records experiments we ran, what we learned, and why certain approaches were not adopted.

**Philosophy:** "What didn't work" is as valuable as "what worked." This log saves future contributors from repeating the same explorations.

---

## Experiment C: Late Chunking via ColBERT (March 2026)

**Hypothesis:** BGE-M3 supports ColBERT multi-vector retrieval. By encoding a full note once and pooling token-span embeddings per chunk, each chunk would carry full-document context — true "late chunking" as described in the academic literature.

**What we tried:**
- `BGEM3FlagModel.encode(return_colbert_vecs=True)` via FlagEmbedding (Apache 2.0)
- ColBERT vectors shape: `(seq_len, 1024)` ✅ — mathematically correct
- Split token sequence into overlapping chunks, mean-pool each span
- Create child `lc-chunk` nodes with `PART_OF` edges to parent note

**Why it works technically:**
The approach is sound. ColBERT vectors do carry full-document context per token. On GPU this would be fast (~ms per note).

**Why we didn't adopt it:**
ColBERT encode on CPU requires a full forward pass through all 24 layers of XLM-RoBERTa-Large (BGE-M3's base model). This takes **2-3 minutes per note** on our Mac Studio M3 Ultra CPU.

Critically, this happens at **every `add_note` call** — not just during initial ingestion. For a system where an agent adds notes in real-time during sessions, this is unacceptable.

- Dense encode (our current approach): ~50ms per note ✅
- ColBERT encode: ~2-3 min per note ❌

**What we learned:**
- ColBERT is GPU-only for production use
- On CPU: use overlap chunking with standard dense encode instead
- Always evaluate latency impact at `add_note` time, not just at ingestion time
- The question "is this a one-time operation?" must account for all users, not just migrating existing data

**Next approach (Experiment D):**
Overlap chunking with standard `model.encode()`:
- Split long notes into chunks with 50% token overlap
- Each chunk encoded with regular dense encode (~50ms)
- Context preserved through overlap, not token-level embeddings
- Same `PART_OF` edge structure

---

## Experiment A: BGE-M3 Sparse Mode (March 2026)

**Hypothesis:** BGE-M3 supports sparse retrieval (lexical weights). Adding sparse vectors to our hybrid pipeline could improve keyword-exact retrieval.

**Result:** Delta 0pp on PCB. Latency +8 seconds per query.

**Why not adopted:** BM25 already covers keyword matching in our pipeline. Sparse mode from BGE-M3 adds significant latency without retrieval benefit on our data distribution.

**Status:** PAUSED. Could revisit if BM25 is removed or for specific use cases.

---

## Experiment B: Session-Level Granularity for LOCOMO (February 2026)

**Hypothesis:** Indexing LOCOMO at session level (one note per session) rather than turn level would improve single-hop and temporal recall.

**Result:**
- Session-level: 32.6% Recall@5 overall, better single-hop (+12.5pp)
- Turn-level: 44.2% Recall@5 overall, better multi-hop (+25.2pp)

**What we learned:** Turn-level granularity wins for multi-hop retrieval (spreading activation works best on fine-grained nodes). Session-level wins for single-hop and temporal. A hybrid (3-5 turns per note) is the theoretical optimum — not yet implemented.

**Current production:** Turn-level with BGE-M3 → 69.4% Recall@5.

---

*Last updated: March 29, 2026*