# HippoGraph — Benchmark Results

## February 2026

---

## Important Context: What We're Measuring and Why

HippoGraph is built for **personal AI agent memory** — associative, emotionally-weighted, decay-based memory optimized for a single user over time. This is architecturally different from systems designed for multi-session conversation recall across many users.

Standard benchmarks like LOCOMO test retrieval over random conversations between strangers. This is a valid test of retrieval mechanics, but it doesn't capture what HippoGraph is actually optimized for: deep associative memory where spreading activation, emotional weighting, and temporal decay interact to surface *personally relevant* context.

We report LOCOMO results for retrieval quality validation. For real-world performance, the meaningful metric is AI-user continuity over time — a personal benchmark we're developing.

---

## LOCOMO Benchmark — Retrieval Quality

Evaluated on [LOCOMO](https://github.com/snap-research/locomo) — 10 multi-session conversations, 272 sessions, 5,882 turns, 1,986 QA pairs.

**Key result: 66.8% Recall@5 at zero LLM infrastructure cost.**

### Best Configuration

| Parameter | Value |
|-----------|-------|
| Dataset | LOCOMO-10 (1,540 queries, excluding adversarial) |
| Metric | Recall@5, MRR |
| LLM calls | **0** (zero — fully local) |
| Embedding model | paraphrase-multilingual-MiniLM-L12-v2 |
| Entity extraction | spaCy (en\_core\_web\_sm + xx\_ent\_wiki\_sm) |
| Retrieval pipeline | Semantic + Spreading Activation + BM25 + Bi-temporal + Cross-Encoder Reranking |
| Blend weights | α=0.6 (semantic), β=0.10 (spreading), γ=0.15 (BM25), δ=0.15 (temporal) |
| Reranking | cross-encoder/ms-marco-MiniLM-L-6-v2, weight=0.3, top-N=20 |
| Granularity | Hybrid (3-turn chunks, ~1,960 notes) |

### Results: Best Configuration

| Category | Queries | Hits | Recall@5 | MRR |
|----------|---------|------|----------|-----|
| **Overall** | **1,540** | **1,028** | **66.8%** | **0.549** |
| Single-hop | 282 | 177 | 62.8% | 0.470 |
| Multi-hop | 321 | 216 | 67.3% | 0.555 |
| Temporal | 96 | 35 | 36.5% | 0.269 |
| Open-domain | 841 | 600 | 71.3% | 0.606 |

### Optimization Journey

| Configuration | Recall@5 | MRR | Notes |
|--------------|----------|-----|-------|
| Session-level (baseline) | 32.6% | 0.223 | 272 notes |
| Turn-level | 44.2% | 0.304 | 5,870 notes |
| Hybrid + Reranking | 65.5% | 0.535 | ~1,960 notes |
| + Bi-temporal δ signal | 66.0% | 0.546 | |
| + Embedding enrichment ❌ | 65.6% | 0.545 | Reverted — polluted embeddings |
| **+ Query decomposition** | **66.8%** | **0.549** | **Best** |

**Key findings:**
- Spreading activation validated: multi-hop improved from 27.4% (session) to 67.3% (best) — +39.9pp
- Hybrid granularity (3-turn chunks) dramatically improves multi-hop retrieval
- Cross-encoder reranking: major contributor to quality improvement
- Temporal queries remain hardest category — fundamental ceiling for retrieval-only, requires reasoning layer

---

## Baseline Comparison

Baseline servers (no spreading activation, no reranking) on full LOCOMO-10:

| System | Recall@5 | Latency P95 | LLM Cost |
|--------|----------|-------------|----------|
| **HippoGraph (full pipeline)** | **66.8%** | ~300ms | **Zero** |
| Cosine-only baseline | 43.8% | 130ms | Zero |
| BM25-only baseline | 44.9% | 50ms | Zero |

**Conclusion:** Spreading activation + reranking delivers +22.6pp over cosine-only baseline.

---

## Competitive Context

⚠️ **Direct numerical comparison across systems is not valid** — different metrics, different datasets, different evaluation dates. Numbers below are from each system's own published benchmarks as of February 2026 and may have changed since.

| System | Metric | Score | Source | Date | What It Measures | LLM Cost |
|--------|--------|-------|--------|------|-----------------|----------|
| **HippoGraph** | **Recall@5** | **66.8%** | This repo | Feb 2026 | Retrieved correct doc in top-5 | **Zero** |
| Mem0 | J-score | 66.9% | [mem0.ai/blog](https://mem0.ai/blog) | Jan 2026 | LLM-judged answer accuracy | Requires LLM |
| Letta/MemGPT | LoCoMo accuracy | 74.0% | [letta.com/research](https://letta.com) | Jan 2026 | LLM-generated answer accuracy | Requires LLM |
| GPT-4 (no memory) | F1 | 32.1% | [LOCOMO paper](https://arxiv.org/abs/2402.17599) | 2024 | Answer text overlap | — |
| Zep/Graphiti | DMR | 94.8% | [getzep.com/blog](https://www.getzep.com) | Jan 2026 | Different dataset entirely | Requires LLM + Neo4j |

> These numbers are snapshots. Each system actively develops and their benchmarks change. We make no claims about their current performance — check their official documentation for up-to-date numbers.

The one meaningful comparison across all systems: **HippoGraph achieves competitive retrieval at zero LLM infrastructure cost**, while all others require LLM API calls for extraction, consolidation, or answer generation.

---

## End-to-End QA — Personal Data

HippoGraph evaluated end-to-end on its own notes: retrieval + Claude Haiku generation + F1/ROUGE vs ground truth.

**This is the more meaningful benchmark for our use case** — questions generated from real personal memory notes, not synthetic conversation data.

| Parameter | Value |
|-----------|-------|
| QA pairs | 1,311 (from 651 personal notes) |
| Generation model | claude-haiku-4-5-20251001 |
| Retrieval LLM cost | **Zero** |

### Results

| Category | F1 | ROUGE-1 | n |
|----------|----|---------|---|
| **Overall** | **38.7%** | **66.8%** | **1,311** |
| Factual | 40.2% | 67.6% | 1,157 |
| Temporal | 29.2% | 58.5% | 54 |
| Entity | 24.9% | 64.5% | 79 |

| Comparison | Metric | Score | Notes |
|------------|--------|-------|-------|
| **HippoGraph E2E** | **F1** | **38.7%** | Zero retrieval cost |
| GPT-4 (no memory) | F1 | 32.1% | [LOCOMO paper](https://arxiv.org/abs/2402.17599), 2024 — +6.6pp improvement |

> F1 scores in the 30-40% range are expected for open-domain QA with exact-match scoring — paraphrased correct answers score low. ROUGE-1 at 66.8% better reflects actual answer quality.

---

## Retrieval Pipeline

```
Query → Temporal Decomposition (strip signal words, detect direction)
                     ↓
          Embedding → ANN Search (HNSW)
                     ↓
          Spreading Activation (3 iterations, decay=0.7)
                     ↓
          BM25 Keyword Search (Okapi BM25, k1=1.5, b=0.75)
                     ↓
          Temporal Scoring (date overlap + chronological ordering)
                     ↓
          Blend: α×semantic + β×spreading + γ×BM25 + δ×temporal
                     ↓
          Cross-Encoder Reranking (ms-marco-MiniLM-L-6-v2)
                     ↓
          Temporal Decay (half-life=30 days)
                     ↓
          Top-K Results
```

---

## Reproduce

```bash
# 1. Start isolated benchmark container
docker-compose -f docker-compose.benchmark.yml up -d --build

# 2. Load dataset and run evaluation (hybrid granularity)
python3 benchmark/locomo_adapter.py --all \
  --api-url http://localhost:5003 \
  --api-key benchmark_key_locomo_2026 \
  --granularity hybrid

# Results saved to benchmark/results/locomo_results.json
```

---

*HippoGraph Pro — self-hosted, zero-LLM-cost, graph-based associative memory. [github.com/artemMprokhorov/hippograph-pro](https://github.com/artemMprokhorov/hippograph-pro)*