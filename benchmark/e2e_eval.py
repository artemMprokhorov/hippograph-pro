#!/usr/bin/env python3
"""
End-to-End QA Evaluation — HippoGraph #11
Pipeline: question → retrieval (top-5) → Claude Haiku generates answer → F1 + ROUGE-1 vs ground truth

Usage (inside benchmark container):
  python3 benchmark/e2e_eval.py --qa benchmark/results/hippograph_qa_with_answers.json
  python3 benchmark/e2e_eval.py --qa benchmark/results/hippograph_qa_with_answers.json --limit 50

Metrics:
  - F1: token overlap between generated and ground truth answer
  - ROUGE-1: unigram recall
  - Exact Match (EM): strict string match after normalization
"""
import json
import os
import sys
import time
import argparse
import urllib.request
import re
import string
from collections import Counter

sys.path.insert(0, "/app/src")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-haiku-4-5-20251001"
RESULTS_OUT = "benchmark/results/e2e_results.json"

# Generation prompt — minimal, no extra context injection
GENERATION_PROMPT = """You are answering questions based solely on the provided context.
Answer concisely in 1-2 sentences. If the context doesn't contain the answer, say "Unknown".
Do not add information not present in the context."""


# ── Metric helpers ──────────────────────────────────────────────────────────

def normalize(text):
    """Lowercase, remove punctuation and extra whitespace."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return " ".join(text.split())


def f1_score(pred, gold):
    """Token-level F1 between predicted and gold answer."""
    pred_tokens = normalize(pred).split()
    gold_tokens = normalize(gold).split()
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = Counter(pred_tokens) & Counter(gold_tokens)
    num_common = sum(common.values())
    if num_common == 0:
        return 0.0
    precision = num_common / len(pred_tokens)
    recall = num_common / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def rouge1(pred, gold):
    """ROUGE-1 recall: fraction of gold unigrams present in prediction."""
    pred_tokens = set(normalize(pred).split())
    gold_tokens = normalize(gold).split()
    if not gold_tokens:
        return 0.0
    hits = sum(1 for t in gold_tokens if t in pred_tokens)
    return hits / len(gold_tokens)


def exact_match(pred, gold):
    return 1.0 if normalize(pred) == normalize(gold) else 0.0


# ── Retrieval ────────────────────────────────────────────────────────────────

def retrieve_context(question, top_k=5):
    """Retrieve top-k notes from HippoGraph."""
    from graph_engine import search_with_activation
    try:
        hits, _ = search_with_activation(question, limit=top_k)
        context_parts = []
        retrieved_ids = []
        for node in hits:
            nid = node["id"]
            content = node.get("content", "")[:500]  # cap per note
            context_parts.append(f"[Note {nid}]: {content}")
            retrieved_ids.append(nid)
        return "\n\n".join(context_parts), retrieved_ids
    except Exception as e:
        return "", []


# ── Generation ───────────────────────────────────────────────────────────────

def generate_answer(question, context, api_key):
    """Call Claude Haiku to generate answer given retrieved context."""
    user_msg = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 150,
        "system": GENERATION_PROMPT,
        "messages": [{"role": "user", "content": user_msg}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data["content"][0]["text"].strip()
    except Exception as e:
        return ""


# ── Engine init ───────────────────────────────────────────────────────────────

def init_engine():
    from database import init_database, get_all_nodes, get_all_edges
    from stable_embeddings import get_model
    from ann_index import get_ann_index
    from graph_cache import get_graph_cache
    from bm25_index import get_bm25_index
    from graph_metrics import get_graph_metrics
    import numpy as np

    init_database()
    get_model()
    nodes = get_all_nodes()
    edges = get_all_edges()

    ai = get_ann_index()
    for n in nodes:
        if n.get("embedding"):
            emb = np.frombuffer(n["embedding"], dtype=np.float32)
            ai.add_vector(n["id"], emb)

    gc = get_graph_cache()
    for e in edges:
        gc.add_edge(e["source_id"], e["target_id"], e["weight"])

    nids = [n["id"] for n in nodes]
    etups = [(e["source_id"], e["target_id"], e["weight"]) for e in edges]
    get_graph_metrics().compute(etups, nids)

    bm25_docs = [(n["id"], n.get("content", "")) for n in nodes]
    get_bm25_index().build(bm25_docs)
    print(f"Engine: {len(nodes)} nodes, {len(edges)} edges")


# ── Main eval loop ────────────────────────────────────────────────────────────

def run_e2e(qa_path, limit=None, top_k=5):
    api_key = ANTHROPIC_API_KEY
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    with open(qa_path) as f:
        qa_pairs = json.load(f)

    # Filter: only pairs that have ground truth answer
    qa_pairs = [q for q in qa_pairs if q.get("answer", "").strip()]
    if limit:
        qa_pairs = qa_pairs[:limit]

    print(f"\nE2E Eval: {len(qa_pairs)} QA pairs, top_k={top_k}")
    print(f"Model: {MODEL}\n")

    results = []
    total_f1 = total_rouge1 = total_em = 0.0
    cat_stats = {}

    for i, qa in enumerate(qa_pairs):
        question = qa["question"]
        gold = qa["answer"]
        category = qa.get("category", "unknown")

        # Step 1: Retrieve context
        context, retrieved_ids = retrieve_context(question, top_k=top_k)

        # Step 2: Generate answer
        if not context:
            generated = "Unknown"
        else:
            generated = generate_answer(question, context, api_key)

        # Step 3: Score
        f1 = f1_score(generated, gold)
        r1 = rouge1(generated, gold)
        em = exact_match(generated, gold)

        total_f1 += f1
        total_rouge1 += r1
        total_em += em

        if category not in cat_stats:
            cat_stats[category] = {"f1": 0.0, "rouge1": 0.0, "em": 0.0, "n": 0}
        cat_stats[category]["f1"] += f1
        cat_stats[category]["rouge1"] += r1
        cat_stats[category]["em"] += em
        cat_stats[category]["n"] += 1

        results.append({
            "question": question,
            "gold": gold,
            "generated": generated,
            "f1": round(f1, 4),
            "rouge1": round(r1, 4),
            "em": em,
            "category": category,
            "retrieved_ids": retrieved_ids
        })

        if (i + 1) % 20 == 0:
            avg_f1 = total_f1 / (i + 1)
            print(f"  [{i+1}/{len(qa_pairs)}] F1={avg_f1*100:.1f}%")

        # Rate limit
        time.sleep(1.5)

    n = len(qa_pairs)
    print(f"\n{'='*60}")
    print(f"  HippoGraph — End-to-End QA Benchmark")
    print(f"{'='*60}")
    print(f"\n  Queries:  {n}")
    print(f"  F1:       {total_f1/n*100:.1f}%")
    print(f"  ROUGE-1:  {total_rouge1/n*100:.1f}%")
    print(f"  EM:       {total_em/n*100:.1f}%")
    print(f"\n  Per category:")
    for cat, s in sorted(cat_stats.items()):
        cn = s["n"]
        print(f"    {cat:12s}: F1={s['f1']/cn*100:.1f}%  ROUGE={s['rouge1']/cn*100:.1f}%  n={cn}")

    # Compare with competitors
    print(f"\n  Comparison:")
    print(f"    HippoGraph E2E F1:  {total_f1/n*100:.1f}%  (zero LLM cost for retrieval)")
    print(f"    Mem0 J-score:       66.9%  (requires LLM for extraction)")
    print(f"    Letta accuracy:     74.0%  (requires LLM for memory management)")
    print(f"    GPT-4 no memory F1: 32.1%")

    summary = {
        "n": n, "top_k": top_k, "model": MODEL,
        "f1": round(total_f1/n, 4),
        "rouge1": round(total_rouge1/n, 4),
        "em": round(total_em/n, 4),
        "per_category": {k: {m: round(v/s["n"], 4) for m,v in s.items() if m != "n"} | {"n": s["n"]}
                         for k, s in cat_stats.items()},
        "results": results
    }

    os.makedirs(os.path.dirname(RESULTS_OUT), exist_ok=True)
    with open(RESULTS_OUT, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved: {RESULTS_OUT}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa", default="benchmark/results/hippograph_qa_with_answers.json")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    t0 = time.time()
    init_engine()
    run_e2e(args.qa, limit=args.limit, top_k=args.top_k)
    print(f"\nTime: {time.time()-t0:.1f}s")
