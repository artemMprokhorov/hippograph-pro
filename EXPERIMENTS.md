# HippoGraph Pro — Experiments Log

This document records experiments we ran, what we learned, and why certain approaches were not adopted.

**Philosophy:** "What didn't work" is as valuable as "what worked."
This log saves future contributors from repeating the same explorations.

---

## Infrastructure & Embeddings

### ChromaDB as Vector Store (Early 2025)
**Hypothesis:** ChromaDB as managed vector database for semantic search.
**Result:** Too slow for real-time retrieval. Latency unacceptable for interactive use.
**What we learned:** Remote/managed vector DBs add network overhead that kills the UX. Moved to local SQLite + FAISS/HNSWlib.

---

### sentence-transformers on M3 Ultra ARM64 (Early 2025)
**Hypothesis:** Use sentence-transformers library directly for embeddings.
**Result:** Segfault on M3 Ultra ARM64 macOS. Reproducible crash, no workaround found.
**What we learned:** sentence-transformers had ARM64 compatibility issues at the time. Switched to direct HuggingFace `transformers` (AutoModel + AutoTokenizer) which was stable.

---

### OpenAI Embeddings API (Early 2025)
**Hypothesis:** Use OpenAI text-embedding-ada-002 for high quality embeddings.
**Result:** Worked, but vendor lock-in, per-token cost, and network latency were dealbreakers.
**What we learned:** Zero LLM cost is non-negotiable for our architecture. Every API call is a dependency we don't control. Moved to fully local models.

---

### Ollama for NER / Entity Extraction (2025)
**Hypothesis:** Use Ollama (local LLM) for high-quality named entity recognition.
**Result:** 35x slower than GLiNER. Acceptable quality but unacceptable latency for real-time ingestion.
**What we learned:** LLM-based NER is overkill for entity extraction. GLiNER (zero-shot NER model, Apache 2.0) matches quality at a fraction of the cost. Ollama was removed entirely from the stack.

---

### MiniLM-384 Embedding Model (2025 → March 2026)
**Hypothesis:** paraphrase-multilingual-MiniLM-L12-v2 as primary embedding model — fast, small, multilingual.
**Result:** Good baseline. LOCOMO Recall@5 = 65.5%.
**Why we moved on:** BGE-M3 (1024-dim, 8192 token context) gave +3.9pp on LOCOMO (69.4%) and first perfect PCB score (100%). MIT license. The upgrade was worth the larger model size.

---

## Retrieval Architecture

### Experiment A: BGE-M3 Sparse Mode (March 2026)
**Hypothesis:** BGE-M3 supports sparse retrieval (lexical weights via learned token importance). Adding sparse vectors to our hybrid pipeline could improve keyword-exact retrieval.
**Result:** Delta 0pp on PCB. Latency +8 seconds per query.
**What we learned:** BM25 already covers keyword matching in our pipeline. BGE-M3 sparse mode adds significant latency without retrieval benefit on our data distribution. Sparse retrieval is redundant when BM25 is present.
**Status:** PAUSED. Could revisit if BM25 is removed or for specific use cases where BM25 fails.

---

### Experiment B: Session-Level vs Turn-Level Granularity (February 2026)
**Hypothesis:** Indexing LOCOMO at session level (one note per session) rather than turn level would improve recall by providing broader context per note.
**Result:**
- Session-level: 32.6% Recall@5 overall, better single-hop (+12.5pp vs turn-level)
- Turn-level: 44.2% Recall@5 overall, dramatically better multi-hop (+25.2pp)

**What we learned:** Turn-level granularity wins for multi-hop retrieval. Spreading activation works best on fine-grained nodes — many small nodes with rich edge connections outperform few large nodes. Session-level wins for single-hop and temporal queries. A hybrid (3-5 turns per note) is the theoretical optimum — not yet implemented.

**Current production:** Turn-level with BGE-M3 → 69.4% Recall@5.

---

### Temporal Reasoning Variant A: Timeline Assembly (March 2026)
**Hypothesis:** Assemble a chronological timeline of events from retrieved notes and re-rank by temporal proximity to the query.
**Result:** +1.1pp on temporal Recall@5 (32.3% total). Not worth the complexity.
**What we learned:** The ceiling for temporal retrieval without LLM reasoning is ~35-40%. ~40% of LOCOMO temporal questions require inference ("would X happen", "what was X likely to do") — not retrievable by any pure embedding approach. Timeline assembly doesn't break this ceiling.

---

### Temporal Reasoning Variant C: Cross-Conversation TEMPORAL Edges (March 2026)
**Hypothesis:** Create TEMPORAL_BEFORE/AFTER edges between notes across different conversations to improve temporal navigation.
**Result:** Invalid for LOCOMO benchmark — creates cross-conversation interference. Notes from different conversations are connected temporally even though they are unrelated.
**What we learned:** Temporal edges must respect conversation boundaries. Cross-conversation temporal linking is only valid for personal memory (single user's continuous timeline), not for multi-conversation benchmarks.
**What we deployed instead:** Timestamp-based temporal edges v2 — TEMPORAL edges within \u00b13 nearest notes by timestamp. +15-20% activation scores on personal memory, chronological grouping improved significantly.

---

### RRF vs Blend Scoring A/B Test (March 2026)
**Hypothesis:** Reciprocal Rank Fusion (RRF) would outperform our hand-tuned blend scoring (\u03b1\u00d7semantic + \u03b2\u00d7spreading + \u03b3\u00d7BM25) by automatically combining ranks without manual weight tuning.
**Result:** Both methods achieved 100% P@5 on our regression suite. No measurable difference.
**What we learned:** At our scale, both approaches converge to similar results. Blend scoring offers more explicit control over the retrieval signal mix. We kept blend as default with `FUSION_METHOD=blend|rrf` toggle for future experimentation.

---

### Experiment C: Late Chunking via ColBERT (March 2026)
**Hypothesis:** BGE-M3 supports ColBERT multi-vector retrieval. By encoding a full note once via `BGEM3FlagModel.encode(return_colbert_vecs=True)` and pooling token-span embeddings per chunk, each chunk would carry full-document context — true "late chunking".

**What we tried:**
- FlagEmbedding `BGEM3FlagModel` (Apache 2.0) installed
- `encode_with_colbert()` wrapper returning `colbert_vecs` shape `(seq_len, 1024)` ✅
- Split token sequence into overlapping chunks, mean-pool each span
- Child `lc-chunk` nodes with `PART_OF` edges to parent note

**Why it works technically:** Sound approach. ColBERT vectors carry full-document context per token. On GPU: milliseconds per note.

**Why we didn't adopt it:**
ColBERT encode on CPU requires a full forward pass through all 24 layers of XLM-RoBERTa-Large. This takes **2-3 minutes per note** on Mac Studio M3 Ultra CPU.

Critically: this happens at **every `add_note` call**, not just during initial ingestion. For new users starting with an empty database, every note addition would block for 2-3 minutes. Unacceptable.

- Dense encode (production): ~50ms per note ✅
- ColBERT encode: ~2-3 min per note ❌

**What we learned:**
- ColBERT is GPU-only for production systems
- Evaluate latency at `add_note` time, not just bulk ingestion time
- "Is this a one-time operation?" must account for ALL users, not just data migration
- The question that broke it: "what about new users with no existing data?"

**Next approach (Experiment D):** Overlap chunking with standard `model.encode()`:
- Split long notes into chunks with 50% token overlap
- Each chunk encoded with regular dense encode (~50ms)
- Context preserved through overlap, not token-level embeddings
- Same `PART_OF` edge structure

---

## Memory Architecture

### Working Memory as Separate Database (working.db) (March 2026)
**Hypothesis:** Separate SQLite database `working.db` for short-term working memory — fast lookup without ANN, prefix-frontal cortex analog.
**Result:** Not implemented. Architecture decision: `update_working_memory` writes directly to `memory.db` with `category=working-memory`. Sleep compute consolidates. Infrastructure works without a third database.
**What we learned:** Adding infrastructure complexity requires clear benefit. `memory.db` with category filtering already provides the fast lookup needed. The "separate DB" was premature optimization.

---

### End-to-End QA with LLM Generation (March 2026)
**Hypothesis:** Add LLM answer generation layer on top of retrieval to compete with Mem0/Letta on end-to-end F1.
**Result:** F1 = 38.7% (vs Mem0 66.9% J-score, Letta 74.0%).
**What we learned:** The gap is explained by methodology, not retrieval quality. Competitors use LLM for extraction AND generation at every step. We use zero LLM cost. End-to-end F1 is not a fair comparison — our retrieval Recall@5 (69.4%) is competitive; generation quality depends on the LLM used downstream, not on our memory system. We publish retrieval metrics only.

---

*Last updated: March 29, 2026*
*Production stack: BGE-M3 (1024-dim) + BM25 + Spreading Activation + bge-reranker-v2-m3*
*Current benchmark: PCB v5 = 100%, LOCOMO Recall@5 = 69.4%*