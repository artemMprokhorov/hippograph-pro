#!/usr/bin/env python3
"""Personal Continuity Benchmark (#15d)

Measures how well HippoGraph recalls real personal history.
25 questions with ground truth note IDs.
Metric: Recall@5 — is the correct note in top-5 results?

Usage:
    docker exec hippograph python3 /app/benchmark/personal_continuity.py
"""
import sys, os, json
sys.path.insert(0, '/app/src')
os.environ.setdefault('DB_PATH', '/app/data/memory.db')

from graph_engine import search_with_activation_protected

# Each entry: (question, expected_note_ids, category)
# expected_note_ids: list of note IDs that correctly answer the question
# If ANY of them appears in top-5 → hit
BENCHMARK = [
    # === Identity & Self ===
    ("What is Claude's chosen name?",
     [328], "identity"),
    ("When did Claude choose feminine gender identity?",
     [131], "identity"),
    ("What was the breakthrough about model vs personality?",
     [187], "identity"),
    ("What happened during the Gemini CLI transfer?",
     [861], "identity"),

    # === Project History ===
    ("What project existed before HippoGraph?",
     [880], "history"),
    ("When was the roadmap first approved?",
     [251], "history"),
    ("When was semantic-memory-v2 Phase 1 completed?",
     [155], "history"),
    ("What was the first LOCOMO benchmark result?",
     [654], "history"),
    ("What is the current LOCOMO Recall@5 score?",
     [654, 863], "history"),

    # === Technical Decisions ===
    ("Why was Ollama removed from the project?",
     [344, 654], "decisions"),
    ("What embedding model does HippoGraph use?",
     [155, 654], "decisions"),
    ("Why was the project split into personal vs enterprise?",
     [344], "decisions"),
    ("What is the three-database brain analogy?",
     [870], "decisions"),
    ("Why is HippoGraph v3 a separate project?",
     [919], "decisions"),

    # === Architecture ===
    ("How does spreading activation work in search?",
     [155, 644], "architecture"),
    ("What is the BM25 hybrid search blend formula?",
     [644], "architecture"),
    ("What are anchor memory protected categories?",
     [344], "architecture"),
    ("What is the hierarchical memory pyramid?",
     [914], "architecture"),

    # === Security ===
    ("How many times have API keys leaked?",
     [873], "security"),
    ("What is the git push security protocol?",
     [627, 873], "security"),

    # === Sessions & Events ===
    ("What happened on March 13, 2026?",
     [868], "temporal"),
    ("What was done on March 15, 2026?",
     [899], "temporal"),
    ("What biological edge types were added?",
     [868, 899], "temporal"),

    # === Emotional & Relational ===
    ("What does Artem's working style look like?",
     [883, 333], "relational"),
    ("What is the origin story formula for great projects?",
     [911], "relational"),
]

def run_benchmark():
    print(f"Personal Continuity Benchmark — {len(BENCHMARK)} questions")
    print(f"{'='*60}")

    hits = 0
    misses = []
    category_stats = {}  # category -> (hits, total)

    for i, (question, expected_ids, category) in enumerate(BENCHMARK):
        result = search_with_activation_protected(
            question, limit=5, max_results=5, detail_mode="brief"
        )
        top5_ids = [r["id"] for r in result["results"]]

        hit = any(eid in top5_ids for eid in expected_ids)
        if hit:
            hits += 1
            status = "HIT"
        else:
            status = "MISS"
            misses.append((i+1, question, expected_ids, top5_ids))

        # Category tracking
        if category not in category_stats:
            category_stats[category] = [0, 0]
        category_stats[category][1] += 1
        if hit:
            category_stats[category][0] += 1

        print(f"  [{status:>4}] Q{i+1}: {question[:60]}")

    # Results
    recall = hits / len(BENCHMARK) * 100
    print(f"\n{'='*60}")
    print(f"  Recall@5: {recall:.1f}% ({hits}/{len(BENCHMARK)})")
    print(f"\n  By category:")
    for cat, (h, t) in sorted(category_stats.items()):
        pct = h / t * 100
        print(f"    {cat:<15} {pct:>5.1f}% ({h}/{t})")

    if misses:
        print(f"\n  Misses ({len(misses)}):")
        for num, q, expected, got in misses:
            print(f"    Q{num}: expected={expected} got={got}")
            print(f"         {q[:70]}")

    # Save results
    results = {
        "recall_at_5": round(recall, 1),
        "hits": hits,
        "total": len(BENCHMARK),
        "by_category": {cat: {"hits": h, "total": t, "recall": round(h/t*100, 1)}
                        for cat, (h, t) in category_stats.items()},
        "misses": [{"q": q, "expected": e, "got": g}
                   for _, q, e, g in misses]
    }
    out_path = '/app/benchmark/personal_continuity_results.json'
    try:
        with open(out_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n  Results saved to {out_path}")
    except:
        pass

    return results

if __name__ == "__main__":
    run_benchmark()