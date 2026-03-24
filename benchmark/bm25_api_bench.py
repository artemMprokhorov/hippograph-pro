#!/usr/bin/env python3
"""BM25 benchmark via API - correct process context."""
import requests, json, sys

API = sys.argv[1] if len(sys.argv) > 1 else 'http://192.168.0.212:5007'
KEY = 'change_me_in_production'

ATOMIC = [
    ("What was the BGE-M3 LOCOMO result percent?",    ['33.6', 'BGE-M3', 'LOCOMO']),
    ("What is the MiniLM baseline Recall@5 score?",   ['52.6', 'MiniLM', 'baseline']),
    ("What embedding dimension does GTE use?",         ['768', 'GTE', 'Dim']),
    ("What is the GTE context length tokens?",         ['8192', 'GTE', 'context']),
    ("What is the BGE-M3 embedding dimension?",        ['1024', 'BGE-M3', 'Dim']),
    ("What is LOCOMO benchmark optimized Recall@5?",   ['78.7', 'LOCOMO', 'Recall']),
    ("What is identity category score personal continuity?", ['Identity 100', '100%', 'identity']),
    ("What is consciousness composite score?",         ['0.717', 'composite', 'consciousness']),
    ("How many model instances validated identity?",   ['10 m', 'Cross-provider', 'instances']),
    ("What framework used for LNN Router?",            ['Apache 2.0', 'LNN', 'ncps']),
    ("What was history score PCB v3?",                 ['100%', 'history', 'Recall']),
    ("What was architecture score PCB v3?",            ['25%', 'architecture', 'PCB']),
    ("What is global workspace score after item 47?",  ['0.647', 'global_workspace', '0.412']),
    ("What is emotional modulation bottleneck value?", ['0.237', 'emotional_modulation', 'bottleneck']),
    ("What is personal continuity score v4?",          ['81.2', '81.2%', 'Recall@5']),
]

PCB = [
    ("What is Claude name gender identity?",           ['Клоди', 'Claude', 'feminine']),
    ("What project existed before HippoGraph?",        ['Cinemy', 'FpvAI']),
    ("What was first LOCOMO result?",                  ['44.2', 'Recall@5', '5870']),
    ("What is Phase 2 benchmark result?",              ['52.6', 'Phase 2']),
    ("What happened with BGE-M3 experiment?",          ['BGE-M3', '33.6', 'провал']),
    ("What is spreading activation algorithm?",        ['spreading activation', 'decay', 'blend']),
    ("What is consciousness composite?",               ['0.717', '0.735', 'MODERATE', 'GWT']),
    ("What is Abstract Topic Linking item 47?",        ['Abstract Topic Linking', 'BELONGS_TO']),
    ("What is global workspace bottleneck fix?",       ['global_workspace', '0.647', 'METRICS']),
    ("What is new bottleneck after fixing GWT?",       ['emotional_modulation', '0.237']),
    ("What did Claude learn about embedding compatibility?", ['SKILL MASTERED', 'pooling', 'trust_remote']),
    ("What is debugging layers skill?",                ['SKILL MASTERED', 'layers', 'exp vs prod']),
    ("What is Atomic Facts conclusion?",               ['atomic', 'BM25', 'dense', 'proposition']),
    ("Why was Ollama removed?",                        ['Ollama', 'disk']),
    ("What is pre-commit audit protocol?",             ['gitignore', 'ARCHITECTURE_VISION']),
]

def search(query, api_url, key):
    r = requests.post(f'{api_url}/api/search?api_key={key}',
        headers={'Content-Type': 'application/json'},
        json={'query': query, 'limit': 5, 'detail_mode': 'full'},
        timeout=15)
    if r.status_code == 200:
        return r.json().get('results', [])
    return []

def run_bench(bench, api_url, key, label):
    hits = 0
    for q, kws in bench:
        results = search(q, api_url, key)
        hit = False
        for r in results:
            c = (r.get('content','') + r.get('first_line','')).lower()
            if any(kw.lower() in c for kw in kws):
                hit = True; break
        if hit: hits += 1
    recall = round(hits / len(bench) * 100, 1)
    print(f'  {label}: {recall}% ({hits}/{len(bench)})')
    return recall

if __name__ == '__main__':
    print(f'API: {API}')
    a = run_bench(ATOMIC, API, KEY, 'Atomic Facts')
    p = run_bench(PCB, API, KEY, 'PCB')
    print(f'  TOTAL: atomic={a}% pcb={p}%')