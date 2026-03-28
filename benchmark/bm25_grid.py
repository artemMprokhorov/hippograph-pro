#!/usr/bin/env python3
import requests, sys
sys.path.insert(0, '/Volumes/Balances/hippograph-pro/benchmark')
from bm25_api_bench import ATOMIC, PCB

PROD_KEY = 'os.environ.get("NEURAL_API_KEY", "change_me")'
BENCH_KEY = 'bench_key'

CONFIGS = [
    ('prod  alpha=0.7 gamma=0.00', 'http://localhost:5001', PROD_KEY),
    ('exp   alpha=0.6 gamma=0.10', 'http://localhost:5020', BENCH_KEY),
    ('exp   alpha=0.6 gamma=0.15', 'http://localhost:5007', 'change_me_in_production'),
    ('exp   alpha=0.6 gamma=0.20', 'http://localhost:5030', BENCH_KEY),
    ('exp   alpha=0.6 gamma=0.25', 'http://localhost:5040', BENCH_KEY),
]

def search(q, url, key):
    try:
        r = requests.post(f'{url}/api/search?api_key={key}',
            headers={'Content-Type': 'application/json'},
            json={'query': q, 'limit': 5, 'detail_mode': 'full'}, timeout=15)
        return r.json().get('results', []) if r.status_code == 200 else []
    except Exception:
        return []

def bench(items, url, key):
    hits = sum(1 for q, kws in items
        if any(any(kw.lower() in (r.get('content','')+r.get('first_line','')).lower()
            for kw in kws) for r in search(q, url, key)))
    return round(hits / len(items) * 100, 1), hits

print('=== BM25 Gamma Grid Search ===')
print(f'{"Config":<35} {"Atomic":>8} {"PCB":>8} {"AVG":>8}')
print('-' * 62)
best = (0, '')
for label, url, key in CONFIGS:
    a, ah = bench(ATOMIC, url, key)
    p, ph = bench(PCB, url, key)
    avg = round((a + p) / 2, 1)
    marker = ' <-- BEST' if avg > best[0] else ''
    print(f'{label:<35} {str(a)+"%":>8} {str(p)+"%":>8} {str(avg)+"%":>8}{marker}')
    if avg > best[0]:
        best = (avg, label)
print(f'\nBest config: {best[1]} (avg={best[0]}%)')