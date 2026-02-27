#!/usr/bin/env python3
"""
Standalone benchmark — no servers needed.
Runs HippoGraph, BM25, and Cosine retrieval directly in-process.
Reads from DB, evaluates QA pairs, prints comparison table.

Usage: python3 benchmark/standalone_eval.py
"""

import json, os, sys, time, sqlite3, math, statistics
from datetime import datetime
from pathlib import Path

BASE = Path("/Volumes/Balances/hippograph-pro")
DB   = BASE / "data/memory.db.backup_20260226_pro_launch"
QA   = BASE / "benchmark/results/hippograph_qa.json"
OUT  = BASE / "benchmark/results/standalone_results.json"
TOP_K = 5

# ── Load data ─────────────────────────────────────────────────

def load_db(db_path):
    conn = sqlite3.connect(str(db_path))
    notes = {r[0]: {"id":r[0],"content":r[1],"category":r[2]}
             for r in conn.execute("SELECT id,content,category FROM nodes")}

    entities = {}
    for node_id, name, etype in conn.execute("""
        SELECT ne.node_id, e.name, e.entity_type
        FROM node_entities ne JOIN entities e ON ne.entity_id=e.id
    """):
        entities.setdefault(node_id, []).append((name, etype))

    edges = {}
    for src, dst, w in conn.execute("SELECT source_id,target_id,weight FROM edges"):
        edges.setdefault(src, []).append((dst, w))
        edges.setdefault(dst, []).append((src, w))

    conn.close()
    return notes, entities, edges

# ── BM25 ──────────────────────────────────────────────────────

def tokenize(text):
    import re
    return re.findall(r'[a-zA-Zа-яА-ЯёЁ0-9]+', text.lower())

def build_bm25_index(notes, k1=1.5, b=0.75):
    from collections import Counter
    corpus = {nid: tokenize(n["content"]) for nid, n in notes.items()}
    N = len(corpus)
    avgdl = sum(len(t) for t in corpus.values()) / max(N, 1)
    df = {}
    for tokens in corpus.values():
        for t in set(tokens):
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log((N - f + 0.5) / (f + 0.5) + 1) for t, f in df.items()}
    return corpus, idf, avgdl, k1, b

def bm25_search(query, corpus, idf, avgdl, k1, b, notes, top_k):
    qtokens = tokenize(query)
    scores = {}
    for nid, tokens in corpus.items():
        dl = len(tokens)
        tf_map = {}
        for t in tokens:
            tf_map[t] = tf_map.get(t, 0) + 1
        score = 0.0
        for t in qtokens:
            if t not in idf: continue
            tf = tf_map.get(t, 0)
            score += idf[t] * (tf * (k1+1)) / (tf + k1*(1 - b + b*dl/avgdl))
        if score > 0:
            scores[nid] = score
    ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
    return [nid for nid, _ in ranked]

# ── Cosine ────────────────────────────────────────────────────

def build_cosine_index(notes):
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        print("  Loading embedding model...")
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        ids = list(notes.keys())
        texts = [notes[i]["content"][:512] for i in ids]
        print(f"  Encoding {len(texts)} notes...")
        embeddings = model.encode(texts, batch_size=64, show_progress_bar=False)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / np.maximum(norms, 1e-9)
        return model, ids, embeddings
    except ImportError:
        return None, None, None

def cosine_search(query, model, ids, embeddings, top_k):
    import numpy as np
    qvec = model.encode([query[:512]])
    qvec = qvec / np.maximum(np.linalg.norm(qvec), 1e-9)
    scores = (embeddings @ qvec.T).flatten()
    top_idx = scores.argsort()[::-1][:top_k]
    return [ids[i] for i in top_idx]

# ── HippoGraph (spreading activation) ────────────────────────

def hippograph_search(query, model, ids, embeddings, edges, notes, top_k,
                      alpha=0.7, n_iter=3, decay=0.7):
    import numpy as np
    # Semantic scores
    qvec = model.encode([query[:512]])
    qvec = qvec / np.maximum(np.linalg.norm(qvec), 1e-9)
    sem_scores_arr = (embeddings @ qvec.T).flatten()
    sem_scores = {ids[i]: float(sem_scores_arr[i]) for i in range(len(ids))}

    # Spreading activation
    activation = dict(sem_scores)
    for _ in range(n_iter):
        new_act = dict(activation)
        for nid, act in activation.items():
            if act < 0.01: continue
            for neighbor, weight in edges.get(nid, []):
                new_act[neighbor] = new_act.get(neighbor, 0) + act * decay * weight
        activation = new_act

    # Blend
    blend = {}
    for nid in notes:
        s = alpha * sem_scores.get(nid, 0) + (1-alpha) * activation.get(nid, 0)
        blend[nid] = s

    ranked = sorted(blend.items(), key=lambda x: -x[1])[:top_k]
    return [nid for nid, _ in ranked]

# ── Eval ──────────────────────────────────────────────────────

def evaluate(name, search_fn, qa_pairs, limit=None):
    pairs = qa_pairs[:limit] if limit else qa_pairs
    cats = {}
    overall = {"hits":0,"total":0,"rr":0.0}
    latencies = []

    for qa in pairs:
        evidence = set(qa.get("evidence_note_ids", []))
        if not evidence: continue
        q = qa["question"]
        cat = qa.get("category", "general")

        t0 = time.time()
        retrieved = search_fn(q)
        latencies.append((time.time()-t0)*1000)

        hit = any(i in evidence for i in retrieved)
        rr = next((1.0/(r+1) for r,i in enumerate(retrieved) if i in evidence), 0.0)

        cats.setdefault(cat, {"hits":0,"total":0,"rr":0.0})
        for d in [cats[cat], overall]:
            d["total"] += 1
            if hit: d["hits"] += 1
            d["rr"] += rr

    def calc(d):
        if not d["total"]: return None
        return {"recall_at_5": round(d["hits"]/d["total"], 4),
                "mrr": round(d["rr"]/d["total"], 4),
                "hits": d["hits"], "queries": d["total"]}

    result = {"overall": calc(overall)}
    for c, d in cats.items():
        result[c] = calc(d)
    sl = sorted(latencies)
    result["latency"] = {
        "p50_ms": round(statistics.median(latencies), 1),
        "p95_ms": round(sl[int(len(sl)*0.95)], 1),
    }
    return result

# ── Table ─────────────────────────────────────────────────────

def print_table(all_results):
    systems = list(all_results.keys())
    cats = ["overall"] + sorted({c for m in all_results.values()
                                  for c in m if c not in ("overall","latency")})
    W = 24
    print(f"\n{'='*72}")
    print(f"  HippoGraph Internal Benchmark — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Metric: Recall@5 / MRR")
    print(f"{'='*72}")
    print(f"{'Category':<14}", end="")
    for s in systems: print(f"  {s:<{W}}", end="")
    print()
    print("-"*(14+W*len(systems)+2*len(systems)))
    for cat in cats:
        print(f"{cat:<14}", end="")
        for s in systems:
            m = all_results[s].get(cat)
            if m:
                print(f"  {m['recall_at_5']*100:>5.1f}% / {m['mrr']:.3f}          ", end="")
            else:
                print(f"  {'N/A':<{W}}", end="")
        print()
    print()
    for label, key in [("P50 latency","p50_ms"),("P95 latency","p95_ms")]:
        print(f"{label:<14}", end="")
        for s in systems:
            lat = all_results[s].get("latency",{})
            val = f"{lat.get(key,'N/A')}ms"
            print(f"  {val:<{W}}", end="")
        print()
    print(f"\n{'='*72}\n")

# ── Main ──────────────────────────────────────────────────────

def main():
    print(f"📂 Loading DB: {DB}")
    notes, entities, edges = load_db(DB)
    print(f"  Notes: {len(notes)}, Edges: {sum(len(v) for v in edges.values())//2}")

    print(f"📋 Loading QA: {QA}")
    with open(QA) as f:
        qa_pairs = json.load(f)
    print(f"  QA pairs: {len(qa_pairs)}")

    all_results = {}

    # ── BM25 ──
    print("\n🟥 BM25 Only")
    corpus, idf, avgdl, k1, b = build_bm25_index(notes)
    all_results["BM25"] = evaluate(
        "BM25",
        lambda q: bm25_search(q, corpus, idf, avgdl, k1, b, notes, TOP_K),
        qa_pairs
    )
    print(f"  Recall@5: {all_results['BM25']['overall']['recall_at_5']*100:.1f}%")

    # ── Cosine + HippoGraph (need embeddings) ──
    print("\n🟨 Loading embeddings for Cosine + HippoGraph...")
    model, emb_ids, embeddings = build_cosine_index(notes)

    if model is None:
        print("  ⚠️  sentence-transformers not available, skipping Cosine + HippoGraph")
    else:
        print("\n🟨 Cosine Only")
        all_results["Cosine"] = evaluate(
            "Cosine",
            lambda q: cosine_search(q, model, emb_ids, embeddings, TOP_K),
            qa_pairs
        )
        print(f"  Recall@5: {all_results['Cosine']['overall']['recall_at_5']*100:.1f}%")

        print("\n🟦 HippoGraph Pro (Semantic + Spreading Activation)")
        all_results["HippoGraph Pro"] = evaluate(
            "HippoGraph Pro",
            lambda q: hippograph_search(q, model, emb_ids, embeddings, edges, notes, TOP_K),
            qa_pairs
        )
        print(f"  Recall@5: {all_results['HippoGraph Pro']['overall']['recall_at_5']*100:.1f}%")

    # Save + print
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "results": all_results},
                  f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved: {OUT}")
    print_table(all_results)


if __name__ == "__main__":
    main()
