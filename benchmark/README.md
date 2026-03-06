# HippoGraph — LOCOMO Benchmark

This directory contains the evaluation pipeline for the [LOCOMO benchmark](https://github.com/snap-research/locomo) — a standardized dataset for testing long-term conversational memory systems.

**Result:** HippoGraph achieves **66.8% Recall@5** at zero LLM cost.

---

## Reproducing Results

### Prerequisites

- Docker + Docker Compose
- ~4GB disk space (LOCOMO dataset + benchmark container)

### Step 1 — Download the LOCOMO dataset

The LOCOMO dataset is released under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) by SNAP Research (Stanford). Download it directly from the source:

```bash
# From the hippograph-pro root directory
curl -L https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json \
  -o benchmark/locomo10.json
```

Or clone their repo and copy:
```bash
git clone https://github.com/snap-research/locomo.git /tmp/locomo
cp /tmp/locomo/data/locomo10.json benchmark/locomo10.json
```

### Step 2 — Start the benchmark container

```bash
# Isolated container on port 5003 — does NOT touch production (port 5001)
docker-compose -f docker-compose.benchmark.yml up -d --build
```

### Step 3 — Run evaluation

```bash
# Full pipeline: load + eval (turn-level granularity)
python3 benchmark/locomo_adapter.py --all \
  --api-url http://localhost:5003 \
  --api-key benchmark_key_locomo_2026 \
  --granularity turn

# Results saved to benchmark/results/locomo_results.json
```

### Step 4 — View results

```bash
python3 benchmark/locomo_eval.py --results benchmark/results/locomo_results.json
```

### Expected output

```
Overall    Recall@5: 66.8%   MRR: 0.304
Single-hop          37.9%
Multi-hop           52.6%
Temporal            22.9%
Open-domain         45.5%
```

> ⚠️ Exact numbers may vary slightly due to FAISS ANN index non-determinism across platforms.
> Seeds are fixed (`random.seed(42)`, `numpy.seed(42)`) for Python-level operations.

---

## Benchmark Architecture

```
Query → Embedding → ANN Search (HNSW)
                     ↓
          Spreading Activation (3 iterations, decay=0.7)
                     ↓
          BM25 Keyword Search (Okapi BM25, k1=1.5, b=0.75)
                     ↓
          Blend Scoring: α×semantic + β×spreading + γ×BM25
                     ↓
          Temporal Decay (half-life=30 days)
                     ↓
          Top-K Results
```

**Blend weights:** α=0.6 (semantic), β=0.25 (spreading activation), γ=0.15 (BM25)

---

## Important Notes on Comparability

⚠️ **These results measure retrieval quality only, not end-to-end QA accuracy.**

| System | Metric | Score | LLM cost |
|--------|--------|-------|----------|
| **HippoGraph** | **Recall@5** | **66.8%** | **$0** |
| Mem0 | LOCOMO J-score | 66.9% | Required |
| Letta | LoCoMo accuracy | 74.0% | Required |
| GPT-4 (no memory) | F1 | 32.1% | Required |

Direct numerical comparison across these metrics is not valid — different metrics measure different things. HippoGraph's Recall@5 measures whether the correct evidence appears in top-5 retrieved results; other systems report LLM-generated answer quality.

---

## Citation

If you use LOCOMO in your work, please cite the original paper:

```bibtex
@article{maharana2024evaluating,
  title={Evaluating very long-term conversational memory of llm agents},
  author={Maharana, Adyasha and Lee, Dong-Ho and Tulyakov, Sergey and Bansal, Mohit and Barbieri, Francesco and Fang, Yuwei},
  journal={arXiv preprint arXiv:2402.17753},
  year={2024}
}
```