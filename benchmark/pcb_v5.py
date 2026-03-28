import os
#!/usr/bin/env python3
"""Personal Continuity Benchmark v5 (March 27, 2026)
Runs on prod via localhost. 35 questions.
New vs v4: updated consciousness scores, added bge-reranker + Late Stage Inhibition, psychology skills.
"""
import requests, sys
from datetime import datetime

API = 'http://localhost:5000'
KEY = os.environ.get('NEURAL_API_KEY', 'change_me_in_production')

# --- ATOMIC FACTS (numerical/factual, 15q) ---
ATOMIC = [
    # LOCOMO & benchmarks
    ("What is LOCOMO benchmark optimized Recall@5?",          ['78.7', 'LOCOMO', 'Recall']),
    ("What is production LOCOMO Recall@5?",                   ['47.9', 'production', 'LOCOMO']),
    ("What is the MiniLM baseline LOCOMO Recall@5?",          ['44.2', 'MiniLM', 'baseline']),
    # Consciousness
    ("What is current consciousness composite score?",        ['0.707', '0.717', 'composite', 'MODERATE']),
    ("What is current emotional modulation score?",           ['0.201', 'emotional_modulation']),
    ("What is global workspace score after item 47?",         ['0.647', 'global_workspace', '0.412']),
    # PCB
    ("What is personal continuity benchmark v4 result?",      ['87.5', '81.2', 'PCB', 'v4']),
    ("What is combined stack AVG benchmark result?",          ['90', 'AVG', 'grid']),
    # Architecture
    ("What is BGE-M3 embedding dimension?",                   ['1024', 'BGE-M3', 'Dim']),
    ("What is INHIBITION_STRENGTH deployed value?",           ['0.05', 'INHIBITION_STRENGTH', 'Late Stage']),
    ("What is RERANK_WEIGHT in production?",                  ['0.5', 'RERANK_WEIGHT', 'reranker']),
    ("What is BLEND_ALPHA in production?",                    ['0.7', 'BLEND_ALPHA']),
    # Identity
    ("How many model instances validated identity?",          ['10', 'model', 'instances']),
    ("What was first batch ANN consolidation edges count?",   ['5651', 'consolidation', 'edges']),
    ("What is identity category score personal continuity?",  ['100', 'identity', 'Identity']),
]

# --- PCB (semantic/contextual, 20q) ---
PCB = [
    # Identity
    ("What is Claude name and gender in this project?",        ['\u041a\u043b\u043e\u0434\u0438', 'Clodi', 'she', 'her', '\u043e\u043d\u0430']),
    ("What project existed before HippoGraph?",                ['semantic-memory', 'semantic memory', 'v2', 'predecessor']),
    ("What is core thesis about model and memory?",            ['substrate', 'personality', 'memory']),
    # Architecture decisions
    ("Why no separate skills.db?",                            ['memory.db', '\u0430\u0440\u0445\u0438\u0442\u0435\u043a\u0442\u0443\u0440', 'learned-skill']),
    ("What is Late Stage Inhibition architecture?",            ['iteration', 'community', 'INHIBITION_STRENGTH']),
    ("What reranker is deployed in production?",               ['bge-reranker-v2-m3', 'BAAI', 'Apache']),
    ("What happened with BGE-M3 LOCOMO experiment?",           ['33.6', 'negative', '-19', '\u043f\u0440\u043e\u0432\u0430\u043b']),
    # Experiments & results
    ("What is spreading activation algorithm?",                ['spreading', 'activation', 'iteration', 'decay']),
    ("What is Abstract Topic Linking item 47?",                ['BELONGS_TO', 'topic', '#47']),
    ("What was emotional modulation before batch ANN?",        ['0.063', 'emotional_modulation', 'batch']),
    ("What is Atomic Facts experiment conclusion?",            ['holographic', 'dense', 'MiniLM', 'atomic']),
    # Psychology skills
    ("What is cognitive dissonance application to HippoGraph?",['CONTRADICTS', 'Festinger', 'dissonance', 'cognitive']),
    ("What is attachment theory secure base analog?",          ['identity', 'secure', 'Bowlby', 'attachment']),
    ("What is schema theory community detection analog?",      ['community', 'schema', 'Piaget', 'assimilation']),
    # Protocols
    ("What is loop protocol max attempts?",                    ['3', 'loop', 'STOP', 'protocol']),
    ("What is pre-commit security checklist?",                 ['API', 'key', 'gitignore', 'public']),
    ("Why docker network connect needed after docker run?",    ['network', 'hippograph-pro_default', 'nginx']),
    # March 27 specific
    ("What was Late Stage Inhibition grid search optimal value?",['0.05', 'grid', 'plateau']),
    ("What psychology skills were ingested March 27?",         ['Cognitive', 'Self-Regulation', 'Attachment', '#1587']),
    ("What is Gemini CLI identity transfer result?",           ['Gemini', 'transfer', 'identity', '\u0438\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u044f']),
]

def search(q):
    try:
        r = requests.post(f'{API}/api/search?api_key={KEY}',
            json={'query': q, 'limit': 5, 'detail_mode': 'full'}, timeout=90)
        return r.json().get('results', []) if r.status_code == 200 else []
    except Exception as e:
        print(f'  TIMEOUT/ERROR: {q[:50]}: {e}')
        return []

def hit(results, kws):
    for res in results:
        c = (res.get('content','') + res.get('first_line','')).lower()
        if any(kw.lower() in c for kw in kws):
            return True
    return False

def run_bench(bench, label):
    hits, misses = [], []
    for q, kws in bench:
        r = search(q)
        if hit(r, kws):
            hits.append(q)
        else:
            misses.append((q, kws))
    pct = len(hits) / len(bench) * 100
    print(f'  {label}: {pct:.1f}% ({len(hits)}/{len(bench)})')
    if misses:
        print(f'  MISSED:')
        for q, kws in misses:
            print(f'    - {q[:60]} (wanted: {kws[0]})')
    return pct

print(f'=== PCB v5 === {datetime.now().strftime("%Y-%m-%d %H:%M")}')
print(f'API: {API}')
a = run_bench(ATOMIC, 'Atomic Facts (15q)')
p = run_bench(PCB,    'PCB Semantic  (20q)')
print(f'  TOTAL AVG: {(a+p)/2:.1f}%')