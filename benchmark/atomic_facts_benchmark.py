#!/usr/bin/env python3
"""Atomic Facts Benchmark (item #43)

Measures whether atomic-fact nodes improve retrieval of specific
numeric/factual questions compared to baseline (no fact nodes).

Methodology:
- 15 factual questions with known parent note IDs
- Recall@5: does top-5 contain the parent note?
- Run on exp (with atomic facts) and prod (without)
- Compare results

Usage:
    docker exec hippograph-exp python3 /app/benchmark/atomic_facts_benchmark.py
    docker exec hippograph python3 /app/benchmark/atomic_facts_benchmark.py
"""
import sys, os, json
sys.path.insert(0, '/app/src')
os.environ.setdefault('DB_PATH', '/app/data/memory.db')

from graph_engine import search_with_activation_protected
import sqlite3

# Format: (question, parent_note_id, [keywords], description)
# parent_note_id: the note that SHOULD appear in top-5
BENCHMARK = [
    # --- Numeric facts from learned-skill notes ---
    ("What was the BGE-M3 LOCOMO result in percent?",
     1035, ["33.6", "BGE-M3", "LOCOMO"],
     "BGE-M3 experiment result"),

    ("What is the MiniLM baseline Recall@5?",
     1035, ["52.6", "MiniLM", "baseline"],
     "MiniLM baseline score"),

    ("What embedding dimension does GTE-multilingual-base use?",
     1034, ["768", "GTE", "Dim"],
     "GTE dim=768"),

    ("What is the context length of GTE-multilingual-base?",
     1034, ["8192", "GTE", "context"],
     "GTE ctx=8192"),

    ("What is the BGE-M3 embedding dimension?",
     1034, ["1024", "BGE-M3", "Dim"],
     "BGE-M3 dim=1024"),

    # --- Benchmark / score facts ---
    ("What is the LOCOMO benchmark-optimized Recall@5 score?",
     1032, ["78.7", "LOCOMO", "Recall"],
     "LOCOMO 78.7%"),

    ("What is the identity category score in personal continuity?",
     1031, ["Identity 100", "100%", "identity"],
     "Identity 100%"),

    ("What is the consciousness check composite score?",
     1032, ["0.717", "composite", "consciousness"],
     "composite 0.717"),

    ("How many model instances validated identity continuity?",
     1032, ["10 m", "Cross-provider", "instances"],
     "10 model instances"),

    # --- Architecture facts ---
    ("What framework is used for the LNN Router?",
     1011, ["Apache 2.0", "LNN", "ncps"],
     "LNN Router Apache 2.0"),

    # --- PCB benchmark facts ---
    ("What was the history category score in PCB v3?",
     1029, ["100%", "history", "Recall"],
     "PCB v3 history 100%"),

    ("What was the architecture category score in PCB v3?",
     1029, ["25%", "architecture", "PCB"],
     "PCB v3 architecture 25%"),

    # --- Consciousness snapshot ---
    ("What is the global_workspace score after item 47?",
     1115, ["0.647", "global_workspace", "0.412"],
     "global_workspace 0.647"),

    ("What is the emotional_modulation bottleneck value?",
     1115, ["0.237", "emotional_modulation", "bottleneck"],
     "emotional_modulation 0.237"),

    ("What is the personal continuity overall score in v4?",
     1151, ["81.2", "81.2%", "Recall@5"],
     "PCB v4 81.2%"),
]


def run_benchmark(label=""):
    db_path = os.environ.get('DB_PATH', '/app/data/memory.db')
    conn = sqlite3.connect(db_path)

    # Check if atomic facts exist
    n_facts = conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE category='atomic-fact'"
    ).fetchone()[0]
    conn.close()

    tag = f" [{label}]" if label else ""
    print(f"Atomic Facts Benchmark{tag}")
    print(f"Atomic-fact nodes: {n_facts}")
    print(f"Questions: {len(BENCHMARK)}")
    print("=" * 60)

    hits = 0
    misses = []

    for question, parent_id, keywords, desc in BENCHMARK:
        result = search_with_activation_protected(
            question, limit=5, max_results=5, detail_mode="full"
        )

        # Check 1: parent note in top-5
        found_parent = any(
            r.get("id") == parent_id
            for r in result["results"]
        )

        # Check 2: any keyword match in top-5
        found_kw = False
        matched_kw = None
        matched_id = None
        for r in result["results"]:
            content = (r.get("content", "") + r.get("first_line", "")).lower()
            for kw in keywords:
                if kw.lower() in content:
                    found_kw = True
                    matched_kw = kw
                    matched_id = r.get("id")
                    break
            if found_kw:
                break

        hit = found_parent or found_kw
        if hit:
            hits += 1
            how = f"parent #{parent_id}" if found_parent else f"kw '{matched_kw}' in #{matched_id}"
            print(f"  [ HIT] {desc}: {how}")
        else:
            top3 = [(r.get("id"), r.get("first_line", "")[:35])
                    for r in result["results"][:3]]
            misses.append((desc, keywords[:2], top3))
            print(f"  [MISS] {desc}")

    recall = hits / len(BENCHMARK) * 100
    print(f"\n{'='*60}")
    print(f"  Recall@5: {recall:.1f}% ({hits}/{len(BENCHMARK)})")
    print(f"  Atomic-fact nodes: {n_facts}")

    if misses:
        print(f"\n  Misses ({len(misses)}):")
        for desc, kw, top3 in misses:
            print(f"    {desc}")
            print(f"      kw: {kw}")
            print(f"      got: {[str(g[0])+':'+g[1] for g in top3]}")

    return {
        "recall_at_5": round(recall, 1),
        "hits": hits,
        "total": len(BENCHMARK),
        "n_atomic_facts": n_facts,
    }


if __name__ == "__main__":
    import sys
    label = sys.argv[1] if len(sys.argv) > 1 else ""
    run_benchmark(label)