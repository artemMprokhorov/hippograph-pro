#!/usr/bin/env python3
"""Benchmark runner via HTTP API - text-matching evidence detection."""
import json, os, sys, time, urllib.request

API_URL = os.environ.get('API_URL', 'http://127.0.0.1:5000')
API_KEY = os.environ.get('API_KEY', 'bench_key')
LOCOMO = '/app/benchmark/locomo10.json'
OUT_FILE = os.environ.get('OUT_FILE', '/app/benchmark/results/bench_v2_results.json')
TOP_K = 5
CAT_NAMES = {1:'single-hop', 2:'multi-hop', 3:'temporal', 4:'open-domain', 5:'adversarial'}

with open(LOCOMO) as f:
    data = json.load(f)

# Build dia_map per conversation
conversations = []
for ci, item in enumerate(data):
    dia_map = {}
    conv = item.get('conversation', {})
    for key, val in conv.items():
        if not key.startswith('session_') or key.endswith('_date_time'):
            continue
        if not isinstance(val, list):
            continue
        for turn in val:
            did = turn.get('dia_id', '')
            txt = turn.get('text', '')
            if did and txt:
                dia_map[did] = txt
    conversations.append(dia_map)

# Collect QA (skip adversarial)
qas = []
for ci, item in enumerate(data):
    for qa in item.get('qa', []):
        cat = qa.get('category', 0)
        if cat == 5:
            continue
        qas.append({'ci': ci, 'q': qa['question'], 'cat': CAT_NAMES.get(cat, '?'), 'ev': qa.get('evidence', [])})

print('Queries: %d, TOP_K: %d' % (len(qas), TOP_K))
print('API: %s' % API_URL)
print('Output: %s' % OUT_FILE)

stats = {}
t0 = time.time()

for i, qa in enumerate(qas):
    payload = json.dumps({'query': qa['q'], 'limit': TOP_K, 'category': 'locomo-conv%d' % qa['ci']}).encode()
    req = urllib.request.Request('%s/api/search?api_key=%s' % (API_URL, API_KEY), data=payload, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            results = json.loads(resp.read())
    except Exception as e:
        continue

    hit = False
    rank = 0
    for ri, note in enumerate(results.get('results', [])):
        content = note.get('content', '')
        for did in qa['ev']:
            ev_text = conversations[qa['ci']].get(did, '')
            if ev_text and ev_text[:50] in content:
                hit = True
                rank = ri + 1
                break
        if hit:
            break

    c = qa['cat']
    if c not in stats:
        stats[c] = {'tot': 0, 'hits': 0, 'mrr': 0.0}
    stats[c]['tot'] += 1
    if hit:
        stats[c]['hits'] += 1
        stats[c]['mrr'] += 1.0 / rank

    if (i + 1) % 200 == 0:
        t = sum(s['tot'] for s in stats.values())
        h = sum(s['hits'] for s in stats.values())
        print('  [%d/%d] Recall@%d=%.1f%%' % (i + 1, len(qas), TOP_K, h / t * 100))

# Report
print('')
print('=' * 60)
t = sum(s['tot'] for s in stats.values())
h = sum(s['hits'] for s in stats.values())
m = sum(s['mrr'] for s in stats.values())
print('Overall: Recall@%d=%.1f%% (%d/%d) MRR=%.3f' % (TOP_K, h / t * 100, h, t, m / t))
for cn in ['single-hop', 'multi-hop', 'temporal', 'open-domain']:
    if cn in stats:
        s = stats[cn]
        r = s['hits'] / s['tot'] * 100 if s['tot'] else 0
        mr = s['mrr'] / s['tot'] if s['tot'] else 0
        print('  %s: Recall@%d=%5.1f%% (%3d/%3d) MRR=%.3f' % (cn, TOP_K, r, s['hits'], s['tot'], mr))
print('Time: %.1fs' % (time.time() - t0))
with open(OUT_FILE, 'w') as f:
    json.dump({'stats': stats, 'top_k': TOP_K, 'total': t}, f, indent=2)
print('Saved: %s' % OUT_FILE)