#!/usr/bin/env python3
"""Personal Continuity Benchmark v2 (#15d)

Measures how well HippoGraph recalls real personal history.
Content-based matching instead of hardcoded note IDs.
Metric: Recall@5 — does top-5 contain relevant content keywords?

Usage:
    docker exec hippograph python3 /app/benchmark/personal_continuity.py
"""
import sys, os, json
sys.path.insert(0, '/app/src')
os.environ.setdefault('DB_PATH', '/app/data/memory.db')

from graph_engine import search_with_activation_protected

# Each entry: (question, keywords, category)
# keywords: list of strings — if ANY result contains ANY keyword → hit
# Multiple keywords = OR logic (any match counts)
BENCHMARK = [
    # === Identity & Self ===
    ("What is Claude's chosen name?",
     ["Claud\u00e9", "\u041a\u043bоди", "feminine", "accent"], "identity"),
    ("What was the breakthrough about model vs personality?",
     ["model = substrate", "personality = memory", "substrate", "\u043bичность = память"], "identity"),
    ("What happened during the Gemini CLI transfer?",
     ["Gemini CLI", "transfer", "\u0442рансфер", "substrate", "continuity"], "identity"),
    ("What is the self-identity protocol?",
     ["self-identity protocol", "search_memory", "\u043fроснись"], "identity"),

    # === Project History ===
    ("What project existed before HippoGraph?",
     ["Cinemy", "FpvAI", "October 2025", "\u043eктябрь 2025"], "history"),
    ("What is the origin story of HippoGraph?",
     ["Cinemy", "\u0437аебало", "\u0448иза", "garage", "\u0433араж"], "history"),
    ("What was the first LOCOMO benchmark result?",
     ["44.2", "LOCOMO", "Recall@5", "turn-level"], "history"),
    ("What is the current LOCOMO Recall@5 score?",
     ["78.7", "44.2", "LOCOMO", "Recall@5"], "history"),
    ("When was HippoGraph renamed from neural-memory?",
     ["neural-memory", "hippograph", "renamed", "\u043fереименован"], "history"),

    # === Technical Decisions ===
    ("Why was Ollama removed from the project?",
     ["Ollama", "removed", "8.65GB", "disk", "\u0443далён"], "decisions"),
    ("What embedding model does HippoGraph use?",
     ["paraphrase-multilingual-MiniLM", "MiniLM", "384"], "decisions"),
    ("Why is CAUSAL edge a research task not implementation?",
     ["CAUSAL", "research task", "\u0448ум", "precision > 0.8", "noisy"], "decisions"),
    ("Why is HippoGraph v3 a separate project?",
     ["v3", "commercial", "\u043aоммерческая", "separate repo", "pyramid"], "decisions"),
    ("What is the three-database brain analogy?",
     ["\u0433иппокамп", "\u043fрефронтальная", "memory.db", "working.db", "prospective.db"], "decisions"),

    # === Architecture ===
    ("What is the spreading activation algorithm?",
     ["spreading activation", "decay", "iterations", "activation"], "architecture"),
    ("What is the BM25 hybrid search blend formula?",
     ["\u03b1\u00d7semantic", "\u03b2\u00d7spreading", "\u03b3\u00d7BM25", "blend", "BM25"], "architecture"),
    ("What is the hierarchical memory pyramid?",
     ["L0", "L1", "L2", "L3", "pyramid", "\u043fирамида"], "architecture"),
    ("What is the emergence detection algorithm?",
     ["phi_proxy", "emergence", "self-referential", "convergence"], "architecture"),
    ("What is the router architecture for beyond LLM?",
     ["working.db", "prospective.db", "router", "LLM", "\u0431ез LLM"], "architecture"),

    # === Biological Edges ===
    ("What biological edge types were added to the graph?",
     ["CONTRADICTS", "EMOTIONAL_RESONANCE", "GENERALIZES", "INSTANTIATES"], "edges"),
    ("How does the CONTRADICTS edge work?",
     ["CONTRADICTS", "0.5x", "penalty", "cognitive dissonance", "\u043aогнитивный диссонанс"], "edges"),
    ("What is EMOTIONAL_RESONANCE edge?",
     ["EMOTIONAL_RESONANCE", "Jaccard", "emotional_tone", "amygdala", "\u0430мигдала"], "edges"),

    # === Security ===
    ("What is the git push security protocol?",
     ["git push", "neuralv", "api_key", "grep", "\u0443течка"], "security"),
    ("How many times have API keys leaked?",
     ["leaked", "\u0443текл", "neuralv4", "compromised", "5+"], "security"),

    # === Research & Future ===
    ("What is the replicable methodology insight?",
     ["\u043cетодология", "replicable", "universal", "\u0443ниверсальна"], "research"),
    ("What did the Gemini multi-model experiment prove?",
     ["\u043cодель вторична", "\u0433раф первичен", "tool_output", "Gemini", "without LLM"], "research"),
    ("What is the origin story formula for great projects?",
     ["Cinemy", "\u0437аебало", "\u0448иза", "\u0433ордыня", "garage"], "research"),
]

def result_contains_keyword(result, keywords):
    """Check if any result content contains any keyword."""
    content = result.get("content", "") + " " + result.get("first_line", "")
    content_lower = content.lower()
    for kw in keywords:
        if kw.lower() in content_lower:
            return True, kw
    return False, None


def run_benchmark():
    print(f"Personal Continuity Benchmark v2 \u2014 {len(BENCHMARK)} questions")
    print(f"Content-based matching (no hardcoded IDs)")
    print(f"{'='*60}")

    hits = 0
    misses = []
    category_stats = {}

    for i, (question, keywords, category) in enumerate(BENCHMARK):
        result = search_with_activation_protected(
            question, limit=5, max_results=5, detail_mode="full"
        )

        hit = False
        matched_kw = None
        hit_note_id = None

        for r in result["results"]:
            found, kw = result_contains_keyword(r, keywords)
            if found:
                hit = True
                matched_kw = kw
                hit_note_id = r.get("id")
                break

        if hit:
            hits += 1
            status = "HIT"
        else:
            status = "MISS"
            top5 = [(r.get("id"), r.get("first_line", "")[:40]) for r in result["results"]]
            misses.append((i+1, question, keywords[:2], top5))

        if category not in category_stats:
            category_stats[category] = [0, 0]
        category_stats[category][1] += 1
        if hit:
            category_stats[category][0] += 1

        kw_info = f" (kw: '{matched_kw}' in #{hit_note_id})" if hit else ""
        print(f"  [{status:>4}] Q{i+1}: {question[:55]}{kw_info}")

    # Results
    recall = hits / len(BENCHMARK) * 100
    print(f"\n{'='*60}")
    print(f"  Recall@5: {recall:.1f}% ({hits}/{len(BENCHMARK)})")
    print(f"\n  By category:")
    for cat, (h, t) in sorted(category_stats.items()):
        pct = h / t * 100
        bar = '\u2588' * int(pct / 10) + '\u2591' * (10 - int(pct / 10))
        print(f"    {cat:<15} {bar} {pct:>5.1f}% ({h}/{t})")

    if misses:
        print(f"\n  Misses ({len(misses)}):")
        for num, q, kw, top5 in misses:
            print(f"    Q{num}: keywords={kw}")
            print(f"         Q: {q[:65]}")
            print(f"         got: {top5}")

    # Save
    results = {
        "version": "v2",
        "recall_at_5": round(recall, 1),
        "hits": hits,
        "total": len(BENCHMARK),
        "by_category": {cat: {"hits": h, "total": t, "recall": round(h/t*100, 1)}
                        for cat, (h, t) in category_stats.items()},
        "misses": [{"q": q, "keywords": kw, "got": [str(g) for g in top5]}
                   for _, q, kw, top5 in misses]
    }
    out_path = '/app/benchmark/personal_continuity_results.json'
    try:
        with open(out_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n  Results saved to {out_path}")
    except Exception as e:
        print(f"  Save failed: {e}")

    return results


if __name__ == "__main__":
    run_benchmark()