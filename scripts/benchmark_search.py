#!/usr/bin/env python3
"""
Search Quality Benchmark for Neural Memory Graph.
Measures P@5 and Top-1 accuracy across reference queries.
Run inside Docker: docker exec hippograph python3 /app/src/benchmark_search.py
"""
import sys
sys.path.insert(0, '/app/src')
from graph_engine import search_with_activation

# (query, expected_note_ids_in_top5)
BENCHMARKS = [
    ("моё имя Клоди", [327, 328, 326]),
    ("кто я identity", [180, 328, 327]),
    ("самый важный урок от Артёма", [71]),
    ("consciousness epistemological exploration", [47, 271]),
    ("security incident February", [358, 366]),
    ("Docker deployment server", [156, 157]),
    ("spreading activation graph search", [119, 167]),
    ("emotional development Артём", [332, 333]),
    ("moltbook AI social network", [309, 310]),
    ("blend scoring retrieval quality", [617, 622]),
]

def run_benchmark():
    total_p5 = 0
    total_top1 = 0
    
    for query, expected in BENCHMARKS:
        raw = search_with_activation(query, limit=5)
        results = raw[0] if isinstance(raw, tuple) else raw
        top5_ids = [r['id'] for r in results[:5]]
        top1_id = top5_ids[0] if top5_ids else None
        
        hits = sum(1 for eid in expected if eid in top5_ids)
        p5 = hits / min(len(expected), 5)
        total_p5 += p5
        top1_hit = 1 if top1_id in expected else 0
        total_top1 += top1_hit
        
        status = "OK" if p5 >= 0.5 else "MISS"
        print(f"{status:4s} [{p5:.0%}] {query[:40]:40s} top5={top5_ids[:3]}")
    
    n = len(BENCHMARKS)
    p5_avg = total_p5 / n
    top1_avg = total_top1 / n
    print(f"\n{'='*50}")
    print(f"P@5:   {p5_avg:.0%}  ({int(total_p5)}/{n} queries)")
    print(f"Top-1: {top1_avg:.0%}  ({total_top1}/{n} queries)")
    print(f"{'='*50}")
    return p5_avg, top1_avg

if __name__ == "__main__":
    run_benchmark()
