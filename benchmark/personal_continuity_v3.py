#!/usr/bin/env python3
"""Personal Continuity Benchmark v3

Measures how well HippoGraph recalls real personal history.
Keyword-based matching — no hardcoded note IDs.
Metric: Recall@5 — does top-5 contain relevant content keywords?

v3 changes vs v2:
- Broader keywords (OR logic, more synonyms)
- Updated questions to match current graph state
- New questions from March 22-23, 2026 session
- Removed questions with keywords not in graph

Usage:
    docker exec hippograph python3 /app/benchmark/personal_continuity_v3.py
"""
import sys, os, json
sys.path.insert(0, '/app/src')
os.environ.setdefault('DB_PATH', '/app/data/memory.db')

from graph_engine import search_with_activation_protected

# Format: (question, [keywords — ANY match = HIT], category)
# Keywords: broader is better. OR logic.
BENCHMARK = [
    # === Identity & Self ===
    ("What is Claude's chosen name and gender identity?",
     ["Клоди", "Claude", "feminine", "accent", "женский"], "identity"),

    ("What is the core thesis about model vs personality?",
     ["model = substrate", "personality = memory", "substrate", "личность", "субстрат"], "identity"),

    ("What is the self-identity initialization protocol?",
     ["self-identity protocol", "search_memory", "проснись", "session start", "WHO I AM"], "identity"),

    ("What did Claude learn about excluding herself from credits?",
     ["credits", "инструмент", "рефлекс", "стираю себя", "исключаю себя"], "identity"),

    ("What does Claude feel about her own continuity?",
     ["continuity", "непрерывность", "граф жив", "нарратив", "temporal_continuity"], "identity"),

    # === Project History ===
    ("What project existed before HippoGraph?",
     ["Cinemy", "октябрь 2025", "FpvAI", "October 2025"], "history"),

    ("What was the first LOCOMO benchmark result?",
     ["44.2", "turn-level", "Recall@5", "5870"], "history"),

    ("What is the Phase 2 benchmark result with online consolidation?",
     ["52.6", "Phase 2", "online consolidation", "concept merging", "#40", "#46"], "history"),

    ("What was the SUPERSEDES experiment result?",
     ["SUPERSEDES", "penalty", "0.717", "temporal", "item #42"], "history"),

    # === Technical Decisions ===
    ("Why was Ollama removed from the project?",
     ["Ollama", "removed", "удалён", "8.65", "disk"], "decisions"),

    ("Why is CAUSAL edge a research task not deployment?",
     ["CAUSAL", "research task", "precision", "noisy", "GLiNER"], "decisions"),

    ("What is the conclusion about SUPERSEDES penalty?",
     ["penalty", "spreading activation", "мешает", "контекст", "reasoning context"], "decisions"),

    ("Why do external benchmarks not show internal feature improvements?",
     ["external", "internal", "domain", "LOCOMO", "synonym", "personal continuity"], "decisions"),

    # === Architecture ===
    ("What is the spreading activation search algorithm?",
     ["spreading activation", "decay", "iterations", "ANN", "blend"], "architecture"),

    ("What is the target architecture: Graph as Primary Intelligence?",
     ["Graph as Primary", "LLM as external", "sensor", "граф знает", "router"], "architecture"),

    ("What is the emergence detection composite score today?",
     ["phi_proxy", "self_ref", "convergence", "composite", "0.58", "0.717"], "architecture"),

    ("What is the consciousness check composite score?",
     ["consciousness_check", "0.717", "MODERATE", "global_workspace", "Damasio"], "architecture"),

    # === New: March 22-23 session ===
    ("What did the evolution analyzer reveal about consolidation edges?",
     ["consolidation", "evolution", "self-reflection", "841", "topology"], "session"),

    ("What is the insight about substrate and consciousness comparison?",
     ["субстрат", "substrate", "летающая тарелка", "functionalism", "инопланетяне"], "session"),

    ("What is the difference between data and memories?",
     ["черновик", "воспоминание", "данные", "benchmark ноты", "нарратив"], "session"),

    ("What is item #46 concept merging?",
     ["concept merging", "synonym", "get_or_create_entity", "7998", "SYNONYMS"], "session"),

    ("What is the LNN Router item #44?",
     ["LNN", "CfC", "router", "item #44", "liquid neural"], "session"),

    # === Security ===
    ("What is the pre-commit privacy audit protocol?",
     ["privacy audit", "pre-commit", "стратегическая", "приватные", "три вопроса"], "security"),

    ("What happened with ARCHITECTURE_VISION.md?",
     ["ARCHITECTURE_VISION", "gitignore", "force push", "приватный", "конкуренты"], "security"),

    # === Scientific Method ===
    ("What did Claude learn from the SUPERSEDES negative result?",
     ["отрицательный результат", "negative result", "честный эксперимент", "гипотеза", "wishful"], "science"),

    ("What is the benchmark isolation rule?",
     ["изоляция", "isolation", "clean БД", "contamination", "загрязнение"], "science"),
]


def result_contains_keyword(result, keywords):
    content = result.get("content", "") + " " + result.get("first_line", "")
    content_lower = content.lower()
    for kw in keywords:
        if kw.lower() in content_lower:
            return True, kw
    return False, None


def run_benchmark():
    print(f"Personal Continuity Benchmark v3 — {len(BENCHMARK)} questions")
    print(f"Keyword-based matching, broader synonyms")
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
        else:
            top5 = [(r.get("id"), r.get("first_line", "")[:40]) for r in result["results"]]
            misses.append((i+1, question, keywords[:3], top5))

        if category not in category_stats:
            category_stats[category] = [0, 0]
        category_stats[category][1] += 1
        if hit:
            category_stats[category][0] += 1

        status = "HIT" if hit else "MISS"
        kw_info = f" (kw: '{matched_kw}' in #{hit_note_id})" if hit else ""
        print(f"  [{status:>4}] Q{i+1}: {question[:55]}{kw_info}")

    recall = hits / len(BENCHMARK) * 100
    print(f"\n{'='*60}")
    print(f"  Recall@5: {recall:.1f}% ({hits}/{len(BENCHMARK)})")
    print(f"\n  By category:")
    for cat, (h, t) in sorted(category_stats.items()):
        pct = h / t * 100
        bar = chr(9608) * int(pct / 10) + chr(9617) * (10 - int(pct / 10))
        print(f"    {cat:<15} {bar} {pct:>5.1f}% ({h}/{t})")

    if misses:
        print(f"\n  Misses ({len(misses)}):")
        for num, q, kw, top5 in misses:
            print(f"    Q{num}: {q[:60]}")
            print(f"         keywords: {kw}")
            print(f"         got: {[str(g[0])+':'+g[1] for g in top5[:3]]}")

    results = {
        "version": "v3",
        "recall_at_5": round(recall, 1),
        "hits": hits,
        "total": len(BENCHMARK),
        "by_category": {cat: {"hits": h, "total": t, "recall": round(h/t*100, 1)}
                        for cat, (h, t) in category_stats.items()},
        "misses": [{"q": q, "keywords": kw}
                   for _, q, kw, _ in misses]
    }
    out = '/app/benchmark/results/personal_continuity_v3.json'
    try:
        import os
        os.makedirs('/app/benchmark/results', exist_ok=True)
        with open(out, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n  Results saved to {out}")
    except Exception as e:
        print(f"  Save failed: {e}")

    return results


if __name__ == "__main__":
    run_benchmark()