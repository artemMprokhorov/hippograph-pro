#!/usr/bin/env python3
"""
LOCOMO End-to-End QA Evaluation
Pipeline: question -> HippoGraph retrieval (top-5) -> Claude Haiku -> F1 + ROUGE-1 vs gold answer

Usage (inside benchmark container):
  # First load LOCOMO data:
  python3 benchmark/locomo_adapter.py --load --api-url http://localhost:5003 --api-key benchmark_key_locomo_2026 --granularity turn

  # Then run E2E eval:
  python3 benchmark/locomo_e2e_eval.py
  python3 benchmark/locomo_e2e_eval.py --limit 50  # quick test
"""
import json
import os
import sys
import time
import argparse
import urllib.request
import string
from collections import Counter

sys.path.insert(0, "/app/src")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-haiku-4-5-20251001"
LOCOMO_DATA = "/app/benchmark/locomo10.json"
RESULTS_OUT = "/app/benchmark/results/locomo_e2e_results.json"

GENERATION_PROMPT = """You are answering questions based solely on the provided context from a conversation history.
Answer with minimum words - ideally 1-5 words. Dates: exact date only. Names: name only. Yes/No: answer Yes or No only. Numbers: number only.
If the context does not contain the answer, say Unknown."""

CAT_NAMES = {1: "single-hop", 2: "multi-hop", 3: "temporal", 4: "open-domain", 5: "adversarial"}


# -- Metrics --

def normalize(text):
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return " ".join(text.split())

def f1_score(pred, gold):
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
    pred_tokens = set(normalize(pred).split())
    gold_tokens = normalize(gold).split()
    if not gold_tokens:
        return 0.0
    hits = sum(1 for t in gold_tokens if t in pred_tokens)
    return hits / len(gold_tokens)

def exact_match(pred, gold):
    return 1.0 if normalize(pred) == normalize(gold) else 0.0


# -- Retrieval --

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


def retrieve_context(question, conv_id, top_k=5):
    from graph_engine import search_with_activation
    try:
        hits, _ = search_with_activation(
            question, limit=top_k,
            category_filter=f"locomo-conv{conv_id}"
        )
        context_parts = []
        retrieved_ids = []
        for node in hits:
            content = node.get("content", "")[:600]
            context_parts.append(content)
            retrieved_ids.append(node["id"])
        return "\n\n".join(context_parts), retrieved_ids
    except Exception as e:
        return "", []


# -- Generation --

def generate_answer(question, context, api_key):
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
            return json.loads(r.read())["content"][0]["text"].strip()
    except Exception as e:
        return ""


# -- Main --

def run_locomo_e2e(limit=None, top_k=5):
    api_key = ANTHROPIC_API_KEY
    if not api_key:
        print("ANTHROPIC_API_KEY not set")
        return

    with open(LOCOMO_DATA) as f:
        data = json.load(f)

    # Collect QA pairs with gold answers
    qa_pairs = []
    for conv_idx, item in enumerate(data):
        for qa in item.get("qa", []):
            cat = qa.get("category", 0)
            if cat == 5:  # skip adversarial
                continue
            answer = str(qa.get("answer", "")).strip()
            if not answer:
                continue
            qa_pairs.append({
                "conv_id": conv_idx,
                "question": qa["question"],
                "gold": answer,
                "category": CAT_NAMES.get(cat, "unknown"),
                "evidence": qa.get("evidence", [])
            })

    if limit:
        qa_pairs = qa_pairs[:limit]

    print(f"\nLOCOMO E2E Eval: {len(qa_pairs)} QA pairs, top_k={top_k}")
    print(f"Model: {MODEL}\n")

    results = []
    total_f1 = total_rouge1 = total_em = 0.0
    cat_stats = {}

    for i, qa in enumerate(qa_pairs):
        context, retrieved_ids = retrieve_context(qa["question"], qa["conv_id"], top_k)
        generated = generate_answer(qa["question"], context, api_key) if context else "Unknown"

        f1 = f1_score(generated, qa["gold"])
        r1 = rouge1(generated, qa["gold"])
        em = exact_match(generated, qa["gold"])

        total_f1 += f1
        total_rouge1 += r1
        total_em += em

        cat = qa["category"]
        if cat not in cat_stats:
            cat_stats[cat] = {"f1": 0.0, "rouge1": 0.0, "em": 0.0, "n": 0}
        cat_stats[cat]["f1"] += f1
        cat_stats[cat]["rouge1"] += r1
        cat_stats[cat]["em"] += em
        cat_stats[cat]["n"] += 1

        results.append({
            "question": qa["question"],
            "gold": qa["gold"],
            "generated": generated,
            "f1": round(f1, 4),
            "rouge1": round(r1, 4),
            "em": em,
            "category": cat,
            "conv_id": qa["conv_id"]
        })

        if (i + 1) % 100 == 0:
            avg_f1 = total_f1 / (i + 1)
            print(f"  [{i+1}/{len(qa_pairs)}] F1={avg_f1*100:.1f}%")

        time.sleep(1.5)

    n = len(qa_pairs)
    print(f"\n{'='*60}")
    print(f"  HippoGraph — LOCOMO End-to-End QA")
    print(f"{'='*60}")
    print(f"  Queries:  {n}")
    print(f"  F1:       {total_f1/n*100:.1f}%")
    print(f"  ROUGE-1:  {total_rouge1/n*100:.1f}%")
    print(f"  EM:       {total_em/n*100:.1f}%")
    print(f"\n  Per category:")
    for cat in ["single-hop", "multi-hop", "temporal", "open-domain"]:
        if cat in cat_stats:
            s = cat_stats[cat]
            cn = s["n"]
            print(f"    {cat:12s}: F1={s['f1']/cn*100:.1f}%  ROUGE={s['rouge1']/cn*100:.1f}%  n={cn}")
    print(f"\n  Comparison:")
    print(f"    HippoGraph LOCOMO F1: {total_f1/n*100:.1f}%  (zero retrieval LLM cost)")
    print(f"    Mem0 J-score:         66.9%  (LLM-as-judge, different metric)")
    print(f"    Letta accuracy:       74.0%  (LLM memory management)")
    print(f"    GPT-4 no memory F1:   32.1%")

    summary = {
        "n": n, "top_k": top_k, "model": MODEL,
        "dataset": "LOCOMO-10 (official)",
        "f1": round(total_f1/n, 4),
        "rouge1": round(total_rouge1/n, 4),
        "em": round(total_em/n, 4),
        "per_category": {
            k: {"f1": round(s["f1"]/s["n"], 4), "rouge1": round(s["rouge1"]/s["n"], 4),
                "em": round(s["em"]/s["n"], 4), "n": s["n"]}
            for k, s in cat_stats.items()
        },
        "results": results
    }

    os.makedirs(os.path.dirname(RESULTS_OUT), exist_ok=True)
    with open(RESULTS_OUT, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved: {RESULTS_OUT}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    t0 = time.time()
    init_engine()
    run_locomo_e2e(limit=args.limit, top_k=args.top_k)
    print(f"\nTime: {time.time()-t0:.1f}s")