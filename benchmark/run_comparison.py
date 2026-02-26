#!/usr/bin/env python3
"""
LOCOMO Benchmark Comparison Runner
Runs retrieval evaluation across multiple backends and produces a comparison table.

Systems compared:
  1. HippoGraph Pro  — spreading activation + BM25 + semantic (port 5001)
  2. Cosine only     — semantic similarity, no graph (port 5021)
  3. BM25 only       — keyword search, no embeddings (port 5020)

All systems use the same LOCOMO dataset, same queries, same metric (Recall@5, MRR).

Usage:
  python run_comparison.py --granularity turn
  python run_comparison.py --granularity session
  python run_comparison.py --granularity turn --queries 200
"""

import json
import os
import sys
import time
import argparse
import urllib.request
import urllib.parse
import statistics
from datetime import datetime

SYSTEMS = [
    {
        "name": "HippoGraph Pro",
        "url": "http://localhost:5001",
        "api_key": "neuralv4_zhmQJuJ0xq_tdR8QwGx-xmOYZe6Lvc3Kplwd6oFIUKbnE5c4moy1nQjZM8B-",
        "skip_load": True,
        "color": "🟦"
    },
    {
        "name": "Cosine Only",
        "url": "http://localhost:5021",
        "api_key": "benchmark_key_locomo_2026",
        "skip_load": False,
        "color": "🟨"
    },
    {
        "name": "BM25 Only",
        "url": "http://localhost:5020",
        "api_key": "benchmark_key_locomo_2026",
        "skip_load": False,
        "color": "🟥"
    },
]

LOCOMO_DATA = "benchmark/locomo10.json"
RESULTS_DIR = "benchmark/results"
TOP_K = 5
CATEGORIES = ["single-hop", "multi-hop", "temporal", "open-domain"]


def http_get(url, timeout=30):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read()), r.status
    except Exception as e:
        return None, str(e)


def http_post(url, payload, timeout=30):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()), r.status
    except Exception as e:
        return None, str(e)


def http_delete(url, timeout=10):
    req = urllib.request.Request(url, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()), r.status
    except Exception as e:
        return None, str(e)


def check_systems():
    print("\n🔍 Checking systems...")
    all_ok = True
    for sys_cfg in SYSTEMS:
        resp, status = http_get(f"{sys_cfg['url']}/health")
        if resp:
            print(f"  ✅ {sys_cfg['name']} — {sys_cfg['url']} ({status})")
        else:
            print(f"  ❌ {sys_cfg['name']} — UNREACHABLE: {status}")
            all_ok = False
    return all_ok


def load_system(sys_cfg, conversations, granularity, chunk_size=3):
    url = sys_cfg["url"]
    key = sys_cfg["api_key"]
    http_delete(f"{url}/api/reset?api_key={key}")
    dia_map = {}
    total = 0

    for conv in conversations:
        conv_id = conv["id"]
        speaker_a = conv["speaker_a"]
        speaker_b = conv["speaker_b"]

        if granularity == "turn":
            for session in conv["sessions"]:
                ts = session["timestamp"]
                for turn in session["turns"]:
                    text = turn.get("text", "")
                    dia_id = turn.get("dia_id", "")
                    speaker = turn.get("speaker", "?")
                    if not text or not dia_id:
                        continue
                    content = f"[{speaker}, {ts}] {text}"
                    resp, _ = http_post(
                        f"{url}/api/add_note?api_key={key}",
                        {"content": content, "category": f"locomo-conv{conv_id}"}
                    )
                    if resp:
                        dia_map[dia_id] = resp.get("id", total + 1)
                        total += 1

        elif granularity == "session":
            for session in conv["sessions"]:
                ts = session["timestamp"]
                lines = [f"[{speaker_a} & {speaker_b} — Session {session['num']}, {ts}]"]
                dia_ids = []
                for turn in session["turns"]:
                    if turn.get("text"):
                        lines.append(f"{turn.get('speaker','?')}: {turn['text']}")
                    if turn.get("dia_id"):
                        dia_ids.append(turn["dia_id"])
                content = "\n".join(lines)
                resp, _ = http_post(
                    f"{url}/api/add_note?api_key={key}",
                    {"content": content, "category": f"locomo-conv{conv_id}"}
                )
                if resp:
                    nid = resp.get("id", total + 1)
                    for dia_id in dia_ids:
                        dia_map[dia_id] = nid
                    total += 1

        elif granularity == "hybrid":
            for session in conv["sessions"]:
                ts = session["timestamp"]
                turns = [t for t in session["turns"] if t.get("text") and t.get("dia_id")]
                for i in range(0, len(turns), chunk_size):
                    chunk = turns[i:i + chunk_size]
                    lines = [f"[{ts}]"]
                    dia_ids = []
                    for turn in chunk:
                        lines.append(f"{turn.get('speaker','?')}: {turn['text']}")
                        dia_ids.append(turn["dia_id"])
                    content = "\n".join(lines)
                    resp, _ = http_post(
                        f"{url}/api/add_note?api_key={key}",
                        {"content": content, "category": f"locomo-conv{conv_id}"}
                    )
                    if resp:
                        nid = resp.get("id", total + 1)
                        for dia_id in dia_ids:
                            dia_map[dia_id] = nid
                        total += 1

    return dia_map, total


def evaluate_system(sys_cfg, qa_pairs, dia_map, limit=None):
    url = sys_cfg["url"]
    key = sys_cfg["api_key"]
    results_by_cat = {cat: {"hits": 0, "total": 0, "rr_sum": 0.0} for cat in CATEGORIES}
    results_by_cat["overall"] = {"hits": 0, "total": 0, "rr_sum": 0.0}
    pairs = qa_pairs[:limit] if limit else qa_pairs
    latencies = []

    for qa in pairs:
        question = qa.get("question", "")
        evidence_dia_ids = qa.get("evidence_dia_ids", [])
        category = qa.get("category", "open-domain")
        if not question or not evidence_dia_ids:
            continue
        evidence_note_ids = {dia_map[d] for d in evidence_dia_ids if d in dia_map}
        if not evidence_note_ids:
            continue

        t0 = time.time()
        resp, _ = http_get(
            f"{url}/api/search?api_key={key}&q={urllib.parse.quote(question)}&limit={TOP_K}"
        )
        latencies.append((time.time() - t0) * 1000)
        if not resp:
            continue

        retrieved_ids = [r["id"] for r in resp.get("results", [])]
        hit = any(nid in evidence_note_ids for nid in retrieved_ids)
        rr = next((1.0 / (rank + 1) for rank, nid in enumerate(retrieved_ids)
                   if nid in evidence_note_ids), 0.0)

        cat_key = category if category in results_by_cat else "open-domain"
        for k in [cat_key, "overall"]:
            results_by_cat[k]["total"] += 1
            if hit:
                results_by_cat[k]["hits"] += 1
            results_by_cat[k]["rr_sum"] += rr

    metrics = {}
    for cat, stats in results_by_cat.items():
        if stats["total"] > 0:
            metrics[cat] = {
                "recall_at_5": stats["hits"] / stats["total"],
                "mrr": stats["rr_sum"] / stats["total"],
                "queries": stats["total"],
                "hits": stats["hits"],
            }
    if latencies:
        metrics["latency"] = {
            "p50_ms": round(statistics.median(latencies), 1),
            "p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 1),
            "mean_ms": round(sum(latencies) / len(latencies), 1),
        }
    return metrics


def print_table(all_results, granularity):
    print(f"\n{'='*72}")
    print(f"  LOCOMO Benchmark — Retrieval Comparison (granularity={granularity})")
    print(f"  Metric: Recall@5 / MRR  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*72}")
    systems = list(all_results.keys())
    cats = ["overall", "single-hop", "multi-hop", "temporal", "open-domain"]

    print(f"\n{'Category':<16}", end="")
    for s in systems:
        print(f"  {s:<22}", end="")
    print()
    print("-" * (16 + 24 * len(systems)))

    for cat in cats:
        print(f"{cat:<16}", end="")
        for s in systems:
            m = all_results[s].get(cat)
            if m:
                print(f"  {m['recall_at_5']*100:>5.1f}% / {m['mrr']:.3f}      ", end="")
            else:
                print(f"  {'N/A':>6} / {'N/A':<12}", end="")
        print()

    for label, key in [("Latency P50", "p50_ms"), ("Latency P95", "p95_ms")]:
        print(f"\n{label:<16}", end="")
        for s in systems:
            lat = all_results[s].get("latency")
            print(f"  {str(lat[key])+'ms' if lat else 'N/A':<22}", end="")
        print()

    print(f"\n{'='*72}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--granularity", choices=["turn", "session", "hybrid"], default="turn")
    parser.add_argument("--queries", type=int, default=None)
    parser.add_argument("--skip-load", action="store_true")
    args = parser.parse_args()

    print(f"\n📂 Loading LOCOMO from {LOCOMO_DATA}...")
    with open(LOCOMO_DATA) as f:
        data = json.load(f)
    conversations = data if isinstance(data, list) else data.get("conversations", [])
    qa_pairs = []
    for conv in conversations:
        for qa in conv.get("qa_pairs", []):
            qa["conv_id"] = conv["id"]
            qa_pairs.append(qa)
    qa_pairs = [q for q in qa_pairs if q.get("category") != "adversarial"]
    print(f"  Conversations: {len(conversations)}, QA pairs: {len(qa_pairs)}")

    if not check_systems():
        print("\n❌ Start baseline servers first:")
        print("   python benchmark/baseline_server.py --mode bm25 --port 5020")
        print("   python benchmark/baseline_server.py --mode cosine --port 5021")
        sys.exit(1)

    all_results = {}

    for sys_cfg in SYSTEMS:
        name = sys_cfg["name"]
        print(f"\n{sys_cfg['color']} {name}  ({sys_cfg['url']})")

        if not args.skip_load and not sys_cfg.get("skip_load"):
            print(f"  📥 Loading {args.granularity}-level notes...")
            t0 = time.time()
            dia_map, total = load_system(sys_cfg, conversations, args.granularity)
            print(f"  ✅ {total} notes in {time.time()-t0:.1f}s")
        else:
            dia_map_path = os.path.join(RESULTS_DIR, "session_dia_map.json")
            if not os.path.exists(dia_map_path):
                print(f"  ⚠️ No dia_map, skipping {name}")
                continue
            with open(dia_map_path) as f:
                raw = json.load(f)
            dia_map = {}
            for k, v in raw.items():
                if isinstance(v, dict):
                    for dia_id in v.get("dia_ids", []):
                        dia_map[dia_id] = k
                else:
                    dia_map[k] = v
            print(f"  📁 dia_map: {len(dia_map)} entries")

        print(f"  🔍 Evaluating {args.queries or len(qa_pairs)} queries...")
        t0 = time.time()
        metrics = evaluate_system(sys_cfg, qa_pairs, dia_map, limit=args.queries)
        print(f"  ✅ Done in {time.time()-t0:.1f}s")
        all_results[name] = metrics

    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out = os.path.join(RESULTS_DIR, f"comparison_{args.granularity}_{ts}.json")
    with open(out, "w") as f:
        json.dump({"timestamp": ts, "granularity": args.granularity, "results": all_results}, f, indent=2)
    print(f"\n💾 Saved: {out}")
    print_table(all_results, args.granularity)


if __name__ == "__main__":
    main()
