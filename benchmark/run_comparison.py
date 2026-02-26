#!/usr/bin/env python3
"""
HippoGraph Retrieval Comparison Runner.

Supports two QA sources:
  --qa locomo   : LOCOMO benchmark dataset (benchmark/locomo10.json)
  --qa hippograph: Our own notes with generated QA (benchmark/results/hippograph_qa.json)

Systems: HippoGraph Pro (5001), Cosine-only (5021), BM25-only (5020)

Usage:
  python run_comparison.py --qa hippograph --granularity skip
  python run_comparison.py --qa locomo --granularity turn
"""

import json, os, sys, time, argparse, urllib.request, urllib.parse, statistics
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

RESULTS_DIR = "benchmark/results"
TOP_K = 5


def http_get(url, timeout=30):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read()), r.status
    except Exception as e:
        return None, str(e)

def http_post(url, payload, timeout=30):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
        headers={"Content-Type": "application/json"}, method="POST")
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

def check_systems(systems):
    print("\n🔍 Checking systems...")
    all_ok = True
    for s in systems:
        resp, status = http_get(f"{s['url']}/health")
        if resp:
            print(f"  ✅ {s['name']} ({s['url']})")
        else:
            print(f"  ❌ {s['name']} UNREACHABLE: {status}")
            all_ok = False
    return all_ok

# ── Load helpers ─────────────────────────────────────────────

def load_notes_into(sys_cfg, notes):
    """Load list of {content, category, original_id} into a baseline system.
       Returns mapping original_id -> new_id."""
    url, key = sys_cfg["url"], sys_cfg["api_key"]
    http_delete(f"{url}/api/reset?api_key={key}")
    id_map = {}
    for n in notes:
        resp, _ = http_post(f"{url}/api/add_note?api_key={key}",
                            {"content": n["content"], "category": n.get("category","general")})
        if resp:
            id_map[n["original_id"]] = resp.get("id")
    return id_map

def load_locomo(sys_cfg, conversations, granularity, chunk_size=3):
    """Load LOCOMO conversations. Returns dia_id -> note_id map."""
    url, key = sys_cfg["url"], sys_cfg["api_key"]
    http_delete(f"{url}/api/reset?api_key={key}")
    dia_map = {}
    total = 0
    for conv in conversations:
        cid = conv["id"]
        if granularity == "turn":
            for session in conv["sessions"]:
                ts = session["timestamp"]
                for turn in session["turns"]:
                    text, dia_id = turn.get("text",""), turn.get("dia_id","")
                    if not text or not dia_id: continue
                    content = f"[{turn.get('speaker','?')}, {ts}] {text}"
                    resp, _ = http_post(f"{url}/api/add_note?api_key={key}",
                                        {"content": content, "category": f"locomo-conv{cid}"})
                    if resp:
                        dia_map[dia_id] = resp.get("id", total+1)
                        total += 1
        elif granularity == "session":
            for session in conv["sessions"]:
                ts = session["timestamp"]
                lines = [f"[{conv['speaker_a']} & {conv['speaker_b']}, {ts}]"]
                dia_ids = []
                for turn in session["turns"]:
                    if turn.get("text"): lines.append(f"{turn.get('speaker','?')}: {turn['text']}")
                    if turn.get("dia_id"): dia_ids.append(turn["dia_id"])
                resp, _ = http_post(f"{url}/api/add_note?api_key={key}",
                                    {"content": "\n".join(lines), "category": f"locomo-conv{cid}"})
                if resp:
                    nid = resp.get("id", total+1)
                    for d in dia_ids: dia_map[d] = nid
                    total += 1
    return dia_map, total

# ── Evaluate ─────────────────────────────────────────────────

def evaluate(sys_cfg, qa_pairs, id_map, limit=None):
    url, key = sys_cfg["url"], sys_cfg["api_key"]
    cats = {}
    overall = {"hits":0,"total":0,"rr_sum":0.0}
    latencies = []
    pairs = qa_pairs[:limit] if limit else qa_pairs

    for qa in pairs:
        q = qa.get("question","")
        evidence_orig = qa.get("evidence_note_ids") or qa.get("evidence_dia_ids") or []
        if not q or not evidence_orig: continue

        evidence_ids = {id_map[e] for e in evidence_orig if e in id_map}
        if not evidence_ids: continue

        t0 = time.time()
        resp, _ = http_get(f"{url}/api/search?api_key={key}&q={urllib.parse.quote(q)}&limit={TOP_K}")
        latencies.append((time.time()-t0)*1000)
        if not resp: continue

        retrieved = [r["id"] for r in resp.get("results",[])]
        hit = any(i in evidence_ids for i in retrieved)
        rr = next((1.0/(rank+1) for rank,i in enumerate(retrieved) if i in evidence_ids), 0.0)

        cat = qa.get("category","general")
        if cat not in cats: cats[cat] = {"hits":0,"total":0,"rr_sum":0.0}
        for bucket in [cats[cat], overall]:
            bucket["total"] += 1
            if hit: bucket["hits"] += 1
            bucket["rr_sum"] += rr

    metrics = {"overall": _calc(overall)}
    for cat, stats in cats.items():
        metrics[cat] = _calc(stats)
    if latencies:
        sl = sorted(latencies)
        metrics["latency"] = {
            "p50_ms": round(statistics.median(latencies),1),
            "p95_ms": round(sl[int(len(sl)*0.95)],1),
            "mean_ms": round(sum(latencies)/len(latencies),1),
        }
    return metrics

def _calc(s):
    if s["total"] == 0: return None
    return {"recall_at_5": s["hits"]/s["total"], "mrr": s["rr_sum"]/s["total"],
            "queries": s["total"], "hits": s["hits"]}

# ── Table printer ─────────────────────────────────────────────

def print_table(all_results, title):
    systems = list(all_results.keys())
    # Collect all categories
    all_cats = ["overall"]
    for m in all_results.values():
        for k in m:
            if k not in ("latency","overall") and k not in all_cats:
                all_cats.append(k)

    print(f"\n{'='*72}")
    print(f"  {title}")
    print(f"  Metric: Recall@5 / MRR  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*72}")
    print(f"\n{'Category':<18}", end="")
    for s in systems: print(f"  {s:<22}", end="")
    print()
    print("-"*(18+24*len(systems)))

    for cat in all_cats:
        print(f"{cat:<18}", end="")
        for s in systems:
            m = all_results[s].get(cat)
            if m:
                print(f"  {m['recall_at_5']*100:>5.1f}% / {m['mrr']:.3f}      ", end="")
            else:
                print(f"  {'N/A':>6} / {'N/A':<12}", end="")
        print()

    for label, key in [("Latency P50","p50_ms"),("Latency P95","p95_ms")]:
        print(f"\n{label:<18}", end="")
        for s in systems:
            lat = all_results[s].get("latency")
            print(f"  {str(lat[key])+'ms' if lat else 'N/A':<22}", end="")
        print()
    print(f"\n{'='*72}\n")

# ── Main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa", choices=["locomo","hippograph"], default="hippograph")
    parser.add_argument("--granularity", choices=["turn","session","hybrid","skip"], default="skip",
                        help="skip = use existing data in systems (for hippograph qa)")
    parser.add_argument("--queries", type=int, default=None)
    parser.add_argument("--systems", nargs="+", default=None,
                        help="Filter systems by name substring")
    args = parser.parse_args()

    # Filter systems if requested
    systems = SYSTEMS
    if args.systems:
        systems = [s for s in SYSTEMS if any(f.lower() in s["name"].lower() for f in args.systems)]

    if not check_systems(systems):
        print("\n❌ Start baseline servers first:")
        print("   python benchmark/baseline_server.py --mode bm25 --port 5020")
        print("   python benchmark/baseline_server.py --mode cosine --port 5021")
        sys.exit(1)

    all_results = {}

    # ── HippoGraph QA mode ──────────────────────────────────────
    if args.qa == "hippograph":
        qa_path = os.path.join(RESULTS_DIR, "hippograph_qa.json")
        if not os.path.exists(qa_path):
            print(f"❌ QA file not found: {qa_path}")
            print("   Run: python benchmark/generate_qa.py --limit 100")
            sys.exit(1)

        with open(qa_path) as f:
            qa_pairs = json.load(f)
        print(f"\n📋 QA pairs: {len(qa_pairs)}")

        # Load notes for baseline systems
        import sqlite3
        db_path = "data/benchmark.db" if os.path.exists("data/benchmark.db") else "data/memory.db"
        conn = sqlite3.connect(db_path)
        notes = [{"original_id": r[0], "content": r[1], "category": r[2]}
                 for r in conn.execute("SELECT id, content, category FROM nodes").fetchall()]
        conn.close()
        print(f"📂 Notes for baselines: {len(notes)}")

        for sys_cfg in systems:
            name = sys_cfg["name"]
            print(f"\n{sys_cfg['color']} {name}")

            if not sys_cfg.get("skip_load") and args.granularity != "skip":
                print("  📥 Loading notes...")
                t0 = time.time()
                id_map = load_notes_into(sys_cfg, notes)
                print(f"  ✅ {len(id_map)} notes in {time.time()-t0:.1f}s")
            elif sys_cfg.get("skip_load"):
                # HippoGraph: note IDs are already real DB ids
                id_map = {n["original_id"]: n["original_id"] for n in notes}
            else:
                # Baselines with skip: assume IDs are sequential from last load
                id_map = {n["original_id"]: i+1 for i, n in enumerate(notes)}

            print(f"  🔍 Evaluating {args.queries or len(qa_pairs)} queries...")
            t0 = time.time()
            metrics = evaluate(sys_cfg, qa_pairs, id_map, limit=args.queries)
            print(f"  ✅ Done in {time.time()-t0:.1f}s")
            all_results[name] = metrics

        title = f"HippoGraph Internal Benchmark — {len(qa_pairs)} QA pairs on {len(notes)} notes"

    # ── LOCOMO mode ─────────────────────────────────────────────
    else:
        locomo_path = "benchmark/locomo10.json"
        if not os.path.exists(locomo_path):
            print(f"❌ LOCOMO not found: {locomo_path}")
            sys.exit(1)

        with open(locomo_path) as f:
            data = json.load(f)
        conversations = data if isinstance(data, list) else data.get("conversations", [])
        qa_pairs = []
        for conv in conversations:
            for qa in conv.get("qa_pairs", []):
                qa["conv_id"] = conv["id"]
                qa_pairs.append(qa)
        qa_pairs = [q for q in qa_pairs if q.get("category") != "adversarial"]
        print(f"\n📋 LOCOMO QA pairs: {len(qa_pairs)}")

        for sys_cfg in systems:
            name = sys_cfg["name"]
            print(f"\n{sys_cfg['color']} {name}")

            if not sys_cfg.get("skip_load") and args.granularity != "skip":
                print(f"  📥 Loading {args.granularity}-level notes...")
                t0 = time.time()
                dia_map, total = load_locomo(sys_cfg, conversations, args.granularity)
                print(f"  ✅ {total} notes in {time.time()-t0:.1f}s")
            else:
                dia_map_path = os.path.join(RESULTS_DIR, "session_dia_map.json")
                if not os.path.exists(dia_map_path):
                    print(f"  ⚠️ No dia_map, skipping")
                    continue
                with open(dia_map_path) as f:
                    raw = json.load(f)
                dia_map = {}
                for k, v in raw.items():
                    if isinstance(v, dict):
                        for d in v.get("dia_ids", []): dia_map[d] = k
                    else:
                        dia_map[k] = v

            # Reuse evaluate — LOCOMO uses evidence_dia_ids
            for qa in qa_pairs:
                qa["evidence_note_ids"] = qa.get("evidence_dia_ids", [])

            print(f"  🔍 Evaluating {args.queries or len(qa_pairs)} queries...")
            t0 = time.time()
            metrics = evaluate(sys_cfg, qa_pairs, dia_map, limit=args.queries)
            print(f"  ✅ Done in {time.time()-t0:.1f}s")
            all_results[name] = metrics

        title = f"LOCOMO Benchmark — granularity={args.granularity}"

    # Save + print
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out = os.path.join(RESULTS_DIR, f"comparison_{args.qa}_{ts}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "qa_source": args.qa, "results": all_results}, f,
                  indent=2, ensure_ascii=False)
    print(f"\n💾 Saved: {out}")
    print_table(all_results, title)


if __name__ == "__main__":
    main()
