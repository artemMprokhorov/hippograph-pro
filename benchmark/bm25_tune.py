#!/usr/bin/env python3
"""BM25 gamma tuning benchmark.
Tests different BLEND_GAMMA values on Atomic Facts + PCB v4 benchmarks.
Usage: docker exec hippograph-exp python3 /app/benchmark/bm25_tune.py
"""
import sys, os, json
sys.path.insert(0, '/app/src')
os.environ.setdefault('DB_PATH', '/app/data/memory.db')

def run_atomic_bench():
    from graph_engine import search_with_activation_protected
    import sqlite3
    BENCHMARK = [
        ("What was the BGE-M3 LOCOMO result?", 1035, ["33.6", "BGE-M3"]),
        ("What is the MiniLM baseline Recall@5?", 1035, ["52.6", "MiniLM"]),
        ("What embedding dimension does GTE use?", 1034, ["768", "GTE", "Dim"]),
        ("What is the GTE context length?", 1034, ["8192", "GTE", "context"]),
        ("What is the BGE-M3 embedding dimension?", 1034, ["1024", "BGE-M3", "Dim"]),
        ("What is the LOCOMO benchmark-optimized Recall@5?", 1032, ["78.7", "LOCOMO"]),
        ("What is identity category score in personal continuity?", 1031, ["Identity 100", "100%"]),
        ("What is consciousness check composite score?", 1032, ["0.717", "composite"]),
        ("How many model instances validated identity?", 1032, ["10 m", "Cross-provider"]),
        ("What framework is used for LNN Router?", 1011, ["Apache 2.0", "LNN"]),
        ("What was history category score in PCB v3?", 1029, ["100%", "history"]),
        ("What was architecture category score in PCB v3?", 1029, ["25%", "architecture"]),
        ("What is global_workspace score after item 47?", 1115, ["0.647", "global_workspace"]),
        ("What is emotional_modulation bottleneck value?", 1115, ["0.237", "emotional_modulation"]),
        ("What is personal continuity overall score in v4?", 1151, ["81.2", "Recall@5"]),
    ]
    hits = 0
    for q, pid, kws in BENCHMARK:
        r = search_with_activation_protected(q, limit=5, max_results=5, detail_mode='full')
        hit = any(r2.get('id') == pid for r2 in r['results'])
        if not hit:
            for r2 in r['results']:
                c = (r2.get('content','') + r2.get('first_line','')).lower()
                if any(kw.lower() in c for kw in kws):
                    hit = True; break
        if hit: hits += 1
    return round(hits / len(BENCHMARK) * 100, 1)


def run_pcb():
    from graph_engine import search_with_activation_protected
    BENCHMARK = [
        ("What is Claude chosen name gender identity?", ["Клоди", "Claude", "feminine"]),
        ("What is core thesis about model vs personality?", ["model = substrate", "personality = memory"]),
        ("What is self-identity initialization protocol?", ["WHO I AM", "search_memory"]),
        ("What project existed before HippoGraph?", ["Cinemy", "FpvAI"]),
        ("What was first LOCOMO benchmark result?", ["44.2", "Recall@5", "5870"]),
        ("What is Phase 2 benchmark result?", ["52.6", "Phase 2"]),
        ("What happened with BGE-M3 experiment?", ["BGE-M3", "33.6", "провалился"]),
        ("Why was Ollama removed?", ["Ollama", "disk"]),
        ("What is spreading activation search algorithm?", ["spreading activation", "decay", "blend"]),
        ("What is consciousness check composite score?", ["0.717", "0.735", "MODERATE", "GWT"]),
        ("What is item 47 Abstract Topic Linking?", ["Abstract Topic Linking", "BELONGS_TO", "global_workspace"]),
        ("What is global workspace bottleneck fix?", ["global_workspace", "0.647", "METRICS SNAPSHOT"]),
        ("What is new bottleneck after fixing global workspace?", ["emotional_modulation", "0.237", "METRICS SNAPSHOT"]),
        ("What is pre-commit privacy audit protocol?", ["gitignore", "force push", "ARCHITECTURE_VISION"]),
        ("What did Claude learn from SUPERSEDES negative result?", ["SKILL MASTERED", "negative result"]),
        ("What is benchmark isolation rule?", ["isolation", "SKILL MASTERED", "production"]),
        ("What did Claude learn about embedding model compatibility?", ["SKILL MASTERED", "trust_remote_code", "pooling"]),
        ("What is debugging skill layers from symptom to cause?", ["SKILL MASTERED", "layers", "exp vs prod"]),
        ("What were GTE benchmark results?", ["GTE", "ROADMAP #27b", "MiniLM"]),
        ("What bug was found in topic nodes after item 47?", ["timestamp", "NULL", "108", "abstract-topic"]),
        ("Why does MiniLM outperform BGE-M3?", ["MiniLM", "dense bi-encoder", "hybrid"]),
        ("What is item 43 Atomic Facts conclusion?", ["atomic", "proposition", "BM25", "dense"]),
    ]
    hits = 0
    for q, kws in BENCHMARK:
        r = search_with_activation_protected(q, limit=5, max_results=5, detail_mode='full')
        hit = False
        for r2 in r['results']:
            c = (r2.get('content','') + r2.get('first_line','')).lower()
            if any(kw.lower() in c for kw in kws):
                hit = True; break
        if hit: hits += 1
    return round(hits / len(BENCHMARK) * 100, 1)


if __name__ == '__main__':
    import graph_engine as ge
    gamma = ge.BLEND_GAMMA
    alpha = ge.BLEND_ALPHA
    print(f'\n=== BM25 Tuning: alpha={alpha}, gamma={gamma} ===')
    atomic = run_atomic_bench()
    print(f'Atomic Facts Benchmark: {atomic}%')
    pcb = run_pcb()
    print(f'PCB (22q): {pcb}%')
    print(f'Summary: atomic={atomic}% pcb={pcb}% gamma={gamma}')