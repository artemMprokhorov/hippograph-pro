"""Baseline performance test for spreading activation search."""
import time
import sys
os_import = __import__('os')
sys.path.insert(0, '/app/src')

QUERIES = [
    "hippograph memory architecture",
    "docker deployment issues",
    "identity continuity across model versions",
    "benchmark results locomo",
    "sleep compute consolidation",
    "contradiction detection",
    "entity extraction gliner",
    "spreading activation algorithm",
    "consciousness research",
    "studio mcp tools",
]

from graph_engine import search_with_activation

print(f'=== SA BASELINE ({len(QUERIES)} queries) ===')
times = []
for q in QUERIES:
    t0 = time.perf_counter()
    results = search_with_activation(q, limit=5)
    t1 = time.perf_counter()
    ms = (t1 - t0) * 1000
    times.append(ms)
    print(f'  {ms:6.1f}ms  [{len(results)} results]  {q[:50]}')

print()
print(f'  min:    {min(times):.1f}ms')
print(f'  max:    {max(times):.1f}ms')
print(f'  mean:   {sum(times)/len(times):.1f}ms')
print(f'  median: {sorted(times)[len(times)//2]:.1f}ms')
print(f'  p95:    {sorted(times)[int(len(times)*0.95)]:.1f}ms')