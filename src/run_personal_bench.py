#!/usr/bin/env python3
"""Run personal continuity benchmark via HTTP API (uses ANN index properly)"""
import sys, os, json, requests
sys.path.insert(0, '/app/benchmark')

API_URL = os.getenv('API_URL', 'http://localhost:5000')
API_KEY = os.getenv('NEURAL_API_KEY', '')

# Import benchmark questions
from personal_continuity import BENCHMARK

hits = 0
total = len(BENCHMARK)
results = []
misses = []

print(f'Personal Continuity Benchmark v2 — {total} questions')
print('=' * 60)

for i, entry in enumerate(BENCHMARK):
    question, keywords, category = entry[0], entry[1], entry[2]
    
    resp = requests.post(
        f'{API_URL}/api/search',
        params={'api_key': API_KEY},
        json={'query': question, 'limit': 5, 'detail_mode': 'brief'},
        timeout=30
    )
    data = resp.json()
    results_text = ' '.join([
        r.get('content', '') for r in data.get('results', [])
    ]).lower()
    
    hit = any(kw.lower() in results_text for kw in keywords)
    if hit:
        hits += 1
        print(f'  [ HIT] Q{i+1}: {question}')
    else:
        print(f'  [MISS] Q{i+1}: {question}')
        misses.append((i+1, question, category))
    results.append({'q': question, 'hit': hit, 'category': category})

print()
print('=' * 60)
print(f'  Recall@5: {hits/total*100:.1f}% ({hits}/{total})')

# By category
cats = {}
for r in results:
    c = r['category']
    cats.setdefault(c, [0, 0])
    cats[c][1] += 1
    if r['hit']: cats[c][0] += 1

print('\n  By category:')
for cat, (h, t) in sorted(cats.items()):
    print(f'    {cat:<15} {h/t*100:.1f}% ({h}/{t})')

if misses:
    print('\n  Misses:')
    for qn, q, cat in misses:
        print(f'    Q{qn} [{cat}]: {q}')