"""
LOCOMO Benchmark Adapter for HippoGraph

Evaluates HippoGraph retrieval quality against the LoCoMo benchmark
(Maharana et al., ACL 2024) — standard benchmark for long-term
conversational memory systems.

Approach: Retrieval-only evaluation (no LLM needed)
- Load LOCOMO conversations as notes into HippoGraph
- Run QA queries through our search pipeline
- Measure Recall@k and P@5 on retrieved passages vs ground truth evidence

Data source: https://github.com/snap-research/locomo
File: data/locomo10.json (10 conversations, ~300 QA pairs)

Usage:
    # Step 1: Download dataset
    python locomo_adapter.py --download

    # Step 2: Load conversations into HippoGraph (creates temp DB)
    python locomo_adapter.py --load

    # Step 3: Run evaluation
    python locomo_adapter.py --eval

    # Step 4: Full pipeline
    python locomo_adapter.py --all

Privacy: All processing is LOCAL. LOCOMO data is synthetic
(fictional characters). No real user data involved.
No LLM API calls needed for retrieval-only evaluation.
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path

# Config
LOCOMO_DATA = "benchmark/locomo10.json"
LOCOMO_URL = "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json"
RESULTS_DIR = "benchmark/results"


# ============================================================
# STEP 1: Download LOCOMO dataset
# ============================================================

def download_dataset():
    """Download locomo10.json from GitHub."""
    import urllib.request
    
    os.makedirs(os.path.dirname(LOCOMO_DATA), exist_ok=True)
    if os.path.exists(LOCOMO_DATA):
        print(f"✅ Dataset already exists: {LOCOMO_DATA}")
        return
    
    print(f"📥 Downloading LOCOMO dataset...")
    urllib.request.urlretrieve(LOCOMO_URL, LOCOMO_DATA)
    size = os.path.getsize(LOCOMO_DATA) / 1024 / 1024
    print(f"✅ Downloaded: {LOCOMO_DATA} ({size:.1f} MB)")


# ============================================================
# STEP 2: Parse dataset — extract conversations and QA pairs
# ============================================================

def parse_dataset():
    """Parse locomo10.json into conversations and QA pairs.
    
    Structure: data[i] has keys: qa, conversation, event_summary, observation, 
    session_summary, sample_id.
    conversation has: speaker_a, speaker_b, session_N_date_time, session_N (list of turns).
    Each turn: {speaker, dia_id, text} or {speaker, img_url, blip_caption, ...}
    QA: {question, answer, category, evidence: [dia_ids]}
    Categories: 1=single-hop, 2=multi-hop, 3=temporal, 4=open-domain, 5=adversarial
    """
    with open(LOCOMO_DATA, "r") as f:
        data = json.load(f)
    
    CAT_NAMES = {1: "single-hop", 2: "multi-hop", 3: "temporal", 
                 4: "open-domain", 5: "adversarial"}
    
    conversations = []
    qa_pairs = []
    
    for conv_idx, item in enumerate(data):
        conv = item["conversation"]
        speaker_a = conv.get("speaker_a", f"Speaker_A_{conv_idx}")
        speaker_b = conv.get("speaker_b", f"Speaker_B_{conv_idx}")
        
        # Extract sessions
        sessions = []
        session_num = 1
        while f"session_{session_num}" in conv:
            session_key = f"session_{session_num}"
            timestamp = conv.get(f"session_{session_num}_date_time", "")
            turns = conv[session_key]
            sessions.append({
                "key": session_key,
                "num": session_num,
                "timestamp": timestamp,
                "turns": turns
            })
            session_num += 1
        
        # Build dia_id → turn mapping for evidence lookup
        dia_map = {}
        for session in sessions:
            for turn in session["turns"]:
                dia_id = turn.get("dia_id", "")
                if dia_id:
                    dia_map[dia_id] = {
                        "text": turn.get("text", ""),
                        "speaker": turn.get("speaker", ""),
                        "session_num": session["num"],
                        "timestamp": session["timestamp"]
                    }
        
        # Extract QA pairs
        qa_items = item.get("qa", [])
        for qa in qa_items:
            qa_pairs.append({
                "conversation_id": conv_idx,
                "question": qa.get("question", ""),
                "answer": qa.get("answer", ""),
                "category": qa.get("category", 0),
                "category_name": CAT_NAMES.get(qa.get("category", 0), "unknown"),
                "evidence": qa.get("evidence", [])
            })
        
        conversations.append({
            "id": conv_idx,
            "speaker_a": speaker_a,
            "speaker_b": speaker_b,
            "sessions": sessions,
            "dia_map": dia_map,
            "qa_count": len(qa_items)
        })
    
    # Stats
    total_turns = sum(len(s["turns"]) for c in conversations for s in c["sessions"])
    total_sessions = sum(len(c["sessions"]) for c in conversations)
    print(f"📊 Parsed: {len(conversations)} conversations, {total_sessions} sessions, "
          f"{total_turns} turns, {len(qa_pairs)} QA pairs")
    
    for conv in conversations:
        turns = sum(len(s["turns"]) for s in conv["sessions"])
        print(f"   Conv {conv['id']}: {conv['speaker_a']} & {conv['speaker_b']}, "
              f"{len(conv['sessions'])} sessions, {turns} turns, {conv['qa_count']} QA")
    
    cats = {}
    for qa in qa_pairs:
        c = qa["category_name"]
        cats[c] = cats.get(c, 0) + 1
    print(f"   QA categories: {cats}")
    
    return conversations, qa_pairs


# ============================================================
# STEP 3: Load conversations into HippoGraph
# ============================================================

def load_into_hippograph(conversations, api_url="http://localhost:5003", api_key=None,
                         granularity="session"):
    """Load LOCOMO into HippoGraph via REST API.
    
    Granularity:
    - "session": one note per session (~272 notes, avg 2692 chars)
    - "turn": one note per dialogue turn (~5882 notes, avg 123 chars)
    
    For benchmark, runs against separate container (port 5003) with clean DB.
    """
    import urllib.request
    
    headers = {"Content-Type": "application/json"}
    
    total_loaded = 0
    session_dia_map = {}
    errors = []
    
    for conv in conversations:
        conv_id = conv["id"]
        speaker_a = conv["speaker_a"]
        speaker_b = conv["speaker_b"]
        
        if granularity == "session":
            for session in conv["sessions"]:
                lines = []
                dia_ids_in_session = []
                timestamp = session["timestamp"]
                lines.append(f"[{speaker_a} & {speaker_b} — Session {session['num']}, {timestamp}]")
                
                for turn in session["turns"]:
                    speaker = turn.get("speaker", "?")
                    text = turn.get("text", "")
                    dia_id = turn.get("dia_id", "")
                    if text:
                        lines.append(f"{speaker}: {text}")
                    if dia_id:
                        dia_ids_in_session.append(dia_id)
                
                content = "\n".join(lines)
                category = f"locomo-conv{conv_id}"
                note_key = f"conv{conv_id}-session_{session['num']}"
                
                session_dia_map[note_key] = {
                    "dia_ids": dia_ids_in_session,
                    "session_num": session["num"],
                    "conv_id": conv_id
                }
                
                payload = json.dumps({"content": content, "category": category})
                req = urllib.request.Request(
                    f"{api_url}/api/add_note?api_key={api_key}",
                    data=payload.encode(), headers=headers, method="POST"
                )
                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        json.loads(resp.read())
                        total_loaded += 1
                except Exception as e:
                    errors.append(f"{note_key}: {e}")
        
        elif granularity == "turn":
            for session in conv["sessions"]:
                timestamp = session["timestamp"]
                for turn in session["turns"]:
                    text = turn.get("text", "")
                    dia_id = turn.get("dia_id", "")
                    speaker = turn.get("speaker", "?")
                    if not text or not dia_id:
                        continue
                    
                    content = f"[{speaker}, {timestamp}] {text}"
                    category = f"locomo-conv{conv_id}"
                    note_key = dia_id
                    
                    session_dia_map[note_key] = {
                        "dia_ids": [dia_id],
                        "session_num": session["num"],
                        "conv_id": conv_id
                    }
                    
                    payload = json.dumps({"content": content, "category": category})
                    req = urllib.request.Request(
                        f"{api_url}/api/add_note?api_key={api_key}",
                        data=payload.encode(), headers=headers, method="POST"
                    )
                    try:
                        with urllib.request.urlopen(req, timeout=30) as resp:
                            json.loads(resp.read())
                            total_loaded += 1
                    except Exception as e:
                        errors.append(f"{note_key}: {e}")
        
        elif granularity == "hybrid":
            CHUNK_SIZE = 3  # turns per note
            for session in conv["sessions"]:
                timestamp = session["timestamp"]
                turns_with_text = [t for t in session["turns"] if t.get("text") and t.get("dia_id")]
                
                for i in range(0, len(turns_with_text), CHUNK_SIZE):
                    chunk = turns_with_text[i:i+CHUNK_SIZE]
                    lines = [f"[{timestamp}]"]
                    dia_ids = []
                    
                    for turn in chunk:
                        speaker = turn.get("speaker", "?")
                        lines.append(f"{speaker}: {turn['text']}")
                        dia_ids.append(turn["dia_id"])
                    
                    content = "\n".join(lines)
                    category = f"locomo-conv{conv_id}"
                    note_key = f"conv{conv_id}-s{session['num']}-chunk{i//CHUNK_SIZE}"
                    
                    session_dia_map[note_key] = {
                        "dia_ids": dia_ids,
                        "session_num": session["num"],
                        "conv_id": conv_id
                    }
                    
                    payload = json.dumps({"content": content, "category": category})
                    req = urllib.request.Request(
                        f"{api_url}/api/add_note?api_key={api_key}",
                        data=payload.encode(), headers=headers, method="POST"
                    )
                    try:
                        with urllib.request.urlopen(req, timeout=30) as resp:
                            json.loads(resp.read())
                            total_loaded += 1
                    except Exception as e:
                        errors.append(f"{note_key}: {e}")
        
        print(f"  ✅ Conv {conv_id} ({speaker_a} & {speaker_b}): loaded")
    
    map_path = os.path.join(RESULTS_DIR, "session_dia_map.json")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(map_path, "w") as f:
        json.dump(session_dia_map, f, indent=2)
    
    print(f"\n📊 Total loaded: {total_loaded} notes (granularity={granularity})")
    if errors:
        print(f"⚠️  Errors: {len(errors)}")
        for e in errors[:3]:
            print(f"   {e}")
    print(f"📁 DIA map saved: {map_path}")
    return session_dia_map


# ============================================================
# STEP 4: Run retrieval evaluation
# ============================================================

def evaluate_retrieval(qa_pairs, conversations, api_url="http://localhost:5003", 
                       api_key="benchmark_key_locomo_2026", top_k=5):
    """Run QA queries through HippoGraph search, measure retrieval quality.
    
    For each QA pair:
    1. Send question to search_memory API
    2. Get top-k results  
    3. Check if any result contains ground truth evidence dia_ids
    4. Record hit/miss per category
    
    Metrics:
    - Recall@k: fraction of QA pairs where evidence found in top-k
    - MRR: Mean Reciprocal Rank of first hit
    - Per-category breakdown
    """
    import urllib.request
    
    # Load session_dia_map
    map_path = os.path.join(RESULTS_DIR, "session_dia_map.json")
    with open(map_path, "r") as f:
        session_dia_map = json.load(f)
    
    # Build reverse map: dia_id → note_key
    dia_to_note = {}
    for note_key, info in session_dia_map.items():
        for dia_id in info["dia_ids"]:
            dia_to_note[dia_id] = note_key
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    
    results = []
    cat_stats = {}
    
    for i, qa in enumerate(qa_pairs):
        question = qa["question"]
        evidence_dias = qa["evidence"]
        category = qa["category_name"]
        conv_id = qa["conversation_id"]
        
        # Skip adversarial (no evidence, answer should be "I don't know")
        if category == "adversarial":
            continue
        
        # Search HippoGraph
        payload = json.dumps({
            "query": question,
            "limit": top_k,
            "detail_mode": "full",
            "category": f"locomo-conv{conv_id}"
        })
        
        req = urllib.request.Request(
            f"{api_url}/api/search?api_key={api_key}",
            data=payload.encode(),
            headers=headers,
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req) as resp:
                search_results = json.loads(resp.read())
        except Exception as e:
            print(f"  ❌ Query {i} failed: {e}")
            continue
        
        # Check if any retrieved note contains evidence dia_ids
        hit = False
        rank = 0
        retrieved_notes = search_results.get("results", [])
        
        for r_idx, note in enumerate(retrieved_notes):
            note_content = note.get("content", "")
            # Check if any evidence turn text appears in retrieved note
            for dia_id in evidence_dias:
                # Look up the actual evidence text from conversations
                conv = conversations[conv_id]
                if dia_id in conv["dia_map"]:
                    evidence_text = conv["dia_map"][dia_id]["text"]
                    if evidence_text and evidence_text[:50] in note_content:
                        if not hit:
                            rank = r_idx + 1
                        hit = True
                        break
            if hit:
                break
        
        # Record result
        result = {
            "qa_idx": i,
            "question": question,
            "category": category,
            "conv_id": conv_id,
            "evidence": evidence_dias,
            "hit": hit,
            "rank": rank if hit else 0,
            "num_retrieved": len(retrieved_notes)
        }
        results.append(result)
        
        # Update category stats
        if category not in cat_stats:
            cat_stats[category] = {"total": 0, "hits": 0, "mrr_sum": 0.0}
        cat_stats[category]["total"] += 1
        if hit:
            cat_stats[category]["hits"] += 1
            cat_stats[category]["mrr_sum"] += 1.0 / rank
        
        # Progress
        if (i + 1) % 50 == 0:
            total_so_far = sum(c["total"] for c in cat_stats.values())
            hits_so_far = sum(c["hits"] for c in cat_stats.values())
            print(f"  Progress: {total_so_far} queries, "
                  f"Recall@{top_k}={hits_so_far/total_so_far*100:.1f}%")
    
    # Final metrics
    print(f"\n{'='*60}")
    print(f"LOCOMO BENCHMARK RESULTS — HippoGraph")
    print(f"{'='*60}")
    
    total = sum(c["total"] for c in cat_stats.values())
    total_hits = sum(c["hits"] for c in cat_stats.values())
    total_mrr = sum(c["mrr_sum"] for c in cat_stats.values())
    
    print(f"\nOverall (excluding adversarial):")
    print(f"  Recall@{top_k}: {total_hits/total*100:.1f}% ({total_hits}/{total})")
    print(f"  MRR: {total_mrr/total:.3f}")
    
    print(f"\nPer category:")
    for cat_name in ["single-hop", "multi-hop", "temporal", "open-domain"]:
        if cat_name in cat_stats:
            cs = cat_stats[cat_name]
            recall = cs["hits"] / cs["total"] * 100 if cs["total"] > 0 else 0
            mrr = cs["mrr_sum"] / cs["total"] if cs["total"] > 0 else 0
            print(f"  {cat_name:12s}: Recall@{top_k}={recall:5.1f}% "
                  f"({cs['hits']:3d}/{cs['total']:3d})  MRR={mrr:.3f}")
    
    # Save results
    os.makedirs(RESULTS_DIR, exist_ok=True)
    results_path = os.path.join(RESULTS_DIR, "locomo_results.json")
    with open(results_path, "w") as f:
        json.dump({
            "metrics": {
                "recall_at_k": total_hits / total,
                "mrr": total_mrr / total,
                "top_k": top_k,
                "total_queries": total,
                "per_category": {k: {
                    "recall": v["hits"] / v["total"] if v["total"] > 0 else 0,
                    "mrr": v["mrr_sum"] / v["total"] if v["total"] > 0 else 0,
                    "total": v["total"],
                    "hits": v["hits"]
                } for k, v in cat_stats.items()}
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n📁 Results saved: {results_path}")
    return cat_stats


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="LOCOMO Benchmark Adapter for HippoGraph")
    parser.add_argument("--download", action="store_true", help="Download LOCOMO dataset")
    parser.add_argument("--parse", action="store_true", help="Parse and show dataset stats")
    parser.add_argument("--load", action="store_true", help="Load into HippoGraph")
    parser.add_argument("--eval", action="store_true", help="Run evaluation")
    parser.add_argument("--all", action="store_true", help="Full pipeline")
    parser.add_argument("--api-url", default="http://localhost:5003", help="HippoGraph API URL")
    parser.add_argument("--api-key", default="benchmark_key_locomo_2026", help="API key")
    parser.add_argument("--granularity", default="session", choices=["session", "turn", "hybrid"],
                        help="Note granularity: session (~272), turn (~5882), hybrid (3-turn groups ~1960)")
    
    args = parser.parse_args()
    
    if args.download or args.all:
        download_dataset()
    
    if args.parse or args.all:
        conversations, qa_pairs = parse_dataset()
    
    if args.load or args.all:
        conversations, qa_pairs = parse_dataset()
        load_into_hippograph(conversations, args.api_url, args.api_key, args.granularity)
    
    if args.eval or args.all:
        conversations, qa_pairs = parse_dataset()
        evaluate_retrieval(qa_pairs, conversations, args.api_url, args.api_key)


if __name__ == "__main__":
    main()
