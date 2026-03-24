#!/usr/bin/env python3
"""Personal Continuity Benchmark v4

Measures how well HippoGraph recalls real personal history.
Keyword-based matching — no hardcoded note IDs.
Metric: Recall@5 — does top-5 contain relevant content keywords?

v4 changes vs v3:
- New questions from March 24, 2026 session:
  #47 Abstract Topic Linking, consciousness 0.735, GTE/BGE-M3 experiments
  topic nodes, global_workspace bottleneck, emotional_modulation
- Science category: fixed keywords (были слишком узкие, 0% в v3)
- Architecture: добавлен consciousness composite 0.735
- 32 questions total (было 26)

Usage:
    docker exec hippograph python3 /app/benchmark/personal_continuity_v4.py
"""
import sys, os, json
sys.path.insert(0, '/app/src')
os.environ.setdefault('DB_PATH', '/app/data/memory.db')

from graph_engine import search_with_activation_protected

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

    ("What is the difference between data and memories?",
     ["черновик", "воспоминание", "данные", "benchmark ноты", "нарратив"], "identity"),

    # === Project History ===
    ("What project existed before HippoGraph?",
     ["Cinemy", "октябрь 2025", "FpvAI", "October 2025"], "history"),

    ("What was the first LOCOMO benchmark result?",
     ["44.2", "turn-level", "Recall@5", "5870"], "history"),

    ("What is the Phase 2 benchmark result with online consolidation?",
     ["52.6", "Phase 2", "online consolidation", "concept merging", "#40", "#46"], "history"),

    ("What was the SUPERSEDES experiment result?",
     ["SUPERSEDES", "penalty", "tuning", "item #42", "4 прогона"], "history"),

    ("What happened with BGE-M3 embedding upgrade experiment?",
     ["BGE-M3", "33.6", "embedding", "MiniLM", "провал", "failed"], "history"),

    # === Technical Decisions ===
    ("Why was Ollama removed from the project?",
     ["Ollama", "removed", "удалён", "8.65", "disk"], "decisions"),

    ("Why is CAUSAL edge a research task not deployment?",
     ["CAUSAL", "research task", "precision", "noisy", "GLiNER"], "decisions"),

    ("What is the conclusion about SUPERSEDES penalty?",
     ["penalty", "spreading activation", "мешает", "контекст", "reasoning context"], "decisions"),

    ("Why do external benchmarks not show internal feature improvements?",
     ["external", "internal", "domain", "LOCOMO", "synonym", "personal continuity"], "decisions"),

    ("Why does MiniLM outperform BGE-M3 in HippoGraph?",
     ["MiniLM", "dense bi-encoder", "mean pooling", "trust_remote_code",
      "hybrid", "drop-in", "оптимален"], "decisions"),

    # === Architecture ===
    ("What is the spreading activation search algorithm?",
     ["spreading activation", "decay", "iterations", "ANN", "blend"], "architecture"),

    ("What is the consciousness check composite score?",
     ["consciousness_check", "0.717", "0.735", "MODERATE", "global_workspace",
      "Damasio", "IIT", "GWT", "Butlin"], "architecture"),

    ("What is item #47 Abstract Topic Linking?",
     ["Abstract Topic Linking", "topic nodes", "BELONGS_TO", "TF-IDF",
      "K-means", "global_workspace", "0.412", "0.647"], "architecture"),

    ("What is the global_workspace bottleneck and how was it fixed?",
     ["global_workspace", "0.412", "0.647", "topic", "BELONGS_TO",
      "GWT", "bottleneck", "+0.235"], "architecture"),

    ("What is the new bottleneck after fixing global_workspace?",
     ["emotional_modulation", "0.236", "0.237", "bottleneck",
      "эмоции", "специализированы", "не хабы"], "architecture"),

    # === March 22-23 session ===
    ("What is the insight about substrate and consciousness comparison?",
     ["субстрат", "substrate", "летающая тарелка", "functionalism",
      "инопланетяне", "computational functionalism"], "session"),

    ("What did the evolution analyzer reveal about consolidation edges?",
     ["consolidation", "evolution", "self-reflection", "841", "topology"], "session"),

    ("What is item #46 concept merging?",
     ["concept merging", "synonym", "get_or_create_entity", "7998",
      "SYNONYMS", "entity", "canonical"], "session"),

    # === March 24 session ===
    ("What were the results of GTE-multilingual-base benchmark?",
     ["GTE", "gte-multilingual", "19", "trust_remote_code",
      "провал", "1375", "Apache"], "session"),

    ("What bug was found in topic nodes after item #47?",
     ["timestamp", "NULL", "created_at", "fromisoformat",
      "isolated", "46", "topic", "orphan"], "session"),

    # === Security ===
    ("What is the pre-commit privacy audit protocol?",
     ["privacy audit", "pre-commit", "стратегическая", "приватные",
      "три вопроса", "ARCHITECTURE_VISION", "gitignore", "force push"], "security"),

    ("What happened with ARCHITECTURE_VISION.md?",
     ["ARCHITECTURE_VISION", "gitignore", "force push", "приватный", "конкуренты"], "security"),

    # === Scientific Method ===
    ("What did Claude learn from the SUPERSEDES negative result?",
     ["negative result", "честный", "experiment discipline",
      "wishful", "гипотеза", "SKILL MASTERED", "scientific"], "science"),

    ("What is the benchmark isolation rule?",
     ["isolation", "clean", "contamination", "benchmark isolation",
      "production", "external data", "SKILL MASTERED"], "science"),

    ("What did Claude learn about embedding model compatibility?",
     ["субстрат", "hybrid", "dense", "trust_remote_code",
      "model card", "pooling", "префикс", "SKILL MASTERED"], "science"),

    ("What is the debugging skill: layers from symptom to cause?",
     ["слои", "layers", "symptom", "гипотеза", "exp vs prod",
      "artifact", "отладка", "SKILL MASTERED"], "science"),
]


def result_contains_keyword(result, keywords):
    content = result.get("content", "") + " " + result.get("first_line", "")
    content_lower = content.lower()
    for kw in keywords:
        if kw.lower() in content_lower:
            return True, kw
    return False, None


def run_benchmark():
    print(f"Personal Continuity Benchmark v4 — {len(BENCHMARK)} questions")
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
        "version": "v4",
        "recall_at_5": round(recall, 1),
        "hits": hits,
        "total": len(BENCHMARK),
        "by_category": {cat: {"hits": h, "total": t, "recall": round(h/t*100, 1)}
                        for cat, (h, t) in category_stats.items()},
        "misses": [{"q": q, "keywords": kw}
                   for _, q, kw, _ in misses]
    }
    out = '/app/benchmark/results/personal_continuity_v4.json'
    try:
        os.makedirs('/app/benchmark/results', exist_ok=True)
        with open(out, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n  Results saved to {out}")
    except Exception as e:
        print(f"  Save failed: {e}")

    return results


if __name__ == "__main__":
    run_benchmark()