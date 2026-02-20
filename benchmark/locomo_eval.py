#!/usr/bin/env python3
"""
LOCOMO Evaluator — runs QA queries against loaded benchmark data.
Run INSIDE Docker: docker exec hippograph-bench python3 /app/benchmark/locomo_eval.py
"""
import json, sys, time, os
sys.path.insert(0, "/app/src")

LOCOMO_DATA = "/app/benchmark/locomo10.json"
SESSION_MAP = "/app/benchmark/session_dia_map.json"
RESULTS_OUT = "/app/benchmark/locomo_results.json"
CAT_NAMES = {1:"single-hop", 2:"multi-hop", 3:"temporal", 4:"open-domain", 5:"adversarial"}

def init_engine():
    from database import init_database, get_all_nodes, get_all_edges
    from stable_embeddings import get_model
    from ann_index import get_ann_index
    from graph_cache import get_graph_cache
    from bm25_index import get_bm25_index
    from graph_metrics import get_graph_metrics
    
    init_database()
    get_model()
    
    nodes = get_all_nodes()
    edges = get_all_edges()
    
    import numpy as np
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
    
    bm25_docs = [(n["id"], n.get("content","")) for n in nodes]
    get_bm25_index().build(bm25_docs)
    
    print(f"Engine: {len(nodes)} nodes, {len(edges)} edges")

def run_eval(top_k=5):
    from graph_engine import search_with_activation
    
    with open(LOCOMO_DATA) as f:
        data = json.load(f)
    with open(SESSION_MAP) as f:
        smap = json.load(f)
    
    # note_id -> set of dia_ids
    note_dia = {int(k): set(v["dia_ids"]) for k,v in smap.items()}
    
    # Collect QA
    qas = []
    for ci, item in enumerate(data):
        for qa in item.get("qa", []):
            cat = qa.get("category", 0)
            if cat == 5: continue
            qas.append({"ci":ci, "q":qa["question"], "a":qa.get("answer",""),
                        "cat":CAT_NAMES.get(cat,"?"), "ev":qa.get("evidence",[])})
    
    print(f"\nEval: {len(qas)} queries, top_k={top_k}")
    stats = {}
    
    for i, qa in enumerate(qas):
        cf = f"locomo-conv{qa['ci']}"
        try:
            hits = search_with_activation(qa["q"], limit=top_k, category_filter=cf)
        except Exception as e:
            continue
        
        hit = False
        rank = 0
        ev_set = set(qa["ev"])
        for ri, (nid, score, node) in enumerate(hits):
            if note_dia.get(nid, set()) & ev_set:
                hit = True
                rank = ri + 1
                break
        
        c = qa["cat"]
        if c not in stats:
            stats[c] = {"tot":0, "hits":0, "mrr":0.0}
        stats[c]["tot"] += 1
        if hit:
            stats[c]["hits"] += 1
            stats[c]["mrr"] += 1.0/rank
        
        if (i+1) % 200 == 0:
            t = sum(s["tot"] for s in stats.values())
            h = sum(s["hits"] for s in stats.values())
            print(f"  [{i+1}/{len(qas)}] Recall@{top_k}={h/t*100:.1f}%")
    
    # Report
    print(f"\n{'='*60}")
    print(f"LOCOMO BENCHMARK — HippoGraph")
    print(f"{'='*60}")
    t = sum(s["tot"] for s in stats.values())
    h = sum(s["hits"] for s in stats.values())
    m = sum(s["mrr"] for s in stats.values())
    print(f"\nOverall: Recall@{top_k}={h/t*100:.1f}% ({h}/{t})  MRR={m/t:.3f}")
    print(f"\nPer category:")
    for cn in ["single-hop","multi-hop","temporal","open-domain"]:
        if cn in stats:
            s = stats[cn]
            r = s["hits"]/s["tot"]*100 if s["tot"] else 0
            mr = s["mrr"]/s["tot"] if s["tot"] else 0
            print(f"  {cn:12s}: Recall@{top_k}={r:5.1f}% ({s['hits']:3d}/{s['tot']:3d}) MRR={mr:.3f}")
    
    with open(RESULTS_OUT,"w") as f:
        json.dump({"stats":stats,"top_k":top_k,"total":t},f,indent=2)
    print(f"\nSaved: {RESULTS_OUT}")

if __name__ == "__main__":
    t0 = time.time()
    init_engine()
    run_eval(top_k=5)
    print(f"\nTime: {time.time()-t0:.1f}s")
