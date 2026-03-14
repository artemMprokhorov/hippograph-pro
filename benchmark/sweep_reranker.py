#!/usr/bin/env python3
"""
Reranker weight sweep: test RERANK_WEIGHT = 0.2, 0.3, 0.4, 0.5, 0.6
Also tests RERANK_ENABLED=false as baseline.
"""

import subprocess, json, sqlite3, time, os

API_URL = "http://localhost:5000"
API_KEY = "locomo_key_2026"
DB_PATH = "/app/data/locomo_test.db"
RESULTS_FILE = "/app/benchmark/results/sweep_reranker.json"
CHUNK_SIZE = "3"  # fixed at baseline

CONFIGS = [
    {"RERANK_ENABLED": "false", "RERANK_WEIGHT": "0.0",  "label": "no_rerank"},
    {"RERANK_ENABLED": "true",  "RERANK_WEIGHT": "0.2",  "label": "weight_0.2"},
    {"RERANK_ENABLED": "true",  "RERANK_WEIGHT": "0.3",  "label": "weight_0.3"},  # baseline
    {"RERANK_ENABLED": "true",  "RERANK_WEIGHT": "0.4",  "label": "weight_0.4"},
    {"RERANK_ENABLED": "true",  "RERANK_WEIGHT": "0.5",  "label": "weight_0.5"},
    {"RERANK_ENABLED": "true",  "RERANK_WEIGHT": "0.6",  "label": "weight_0.6"},
]

def clear_db():
    conn = sqlite3.connect(DB_PATH)
    for t in ['nodes','edges','entities','node_entities']:
        conn.execute(f'DELETE FROM {t}')
    conn.commit()
    conn.close()
    print("  DB cleared")

def parse_results(stdout):
    recall = mrr = None
    per_cat = {}
    lines = stdout.split('\n')
    in_results = False
    for line in lines:
        if 'LOCOMO BENCHMARK RESULTS' in line:
            in_results = True
        if in_results and 'Recall@5:' in line and '%' in line and '(' in line and not any(c in line for c in ['single','multi','temporal','open']):
            try:
                recall = float(line.split('Recall@5:')[1].split('%')[0].strip())
            except: pass
        if in_results and line.strip().startswith('MRR:'):
            try:
                mrr = float(line.split('MRR:')[1].strip())
            except: pass
        for cat in ['single-hop', 'multi-hop', 'temporal', 'open-domain']:
            if in_results and cat in line and 'Recall@5=' in line:
                try:
                    per_cat[cat] = float(line.split('Recall@5=')[1].split('%')[0].strip())
                except: pass
    return recall, mrr, per_cat

def run_benchmark(config):
    label = config['label']
    print(f"\n{'='*50}")
    print(f"Config: {label}")
    print(f"{'='*50}")

    clear_db()
    time.sleep(2)

    env = os.environ.copy()
    env['LOCOMO_CHUNK_SIZE'] = CHUNK_SIZE
    env['DISABLE_CATEGORY_DECAY'] = 'true'
    for k, v in config.items():
        if k != 'label':
            env[k] = v

    log_file = f"/app/benchmark/results/sweep_reranker_{label}.log"
    result = subprocess.run(
        ['python3', '/app/benchmark/locomo_adapter.py', '--all',
         '--api-url', API_URL, '--api-key', API_KEY,
         '--granularity', 'hybrid'],
        capture_output=True, text=True, env=env
    )
    with open(log_file, 'w') as f:
        f.write(result.stdout)
        if result.stderr:
            f.write('\nSTDERR:\n' + result.stderr)

    recall, mrr, per_cat = parse_results(result.stdout)
    return {**config, 'recall_at_5': recall, 'mrr': mrr, 'per_category': per_cat, 'log': log_file}

def main():
    results = []
    for config in CONFIGS:
        r = run_benchmark(config)
        results.append(r)
        print(f"  Result: Recall@5={r['recall_at_5']}%, MRR={r['mrr']}")
        with open(RESULTS_FILE, 'w') as f:
            json.dump(results, f, indent=2)

    print("\n" + "="*60)
    print("RERANKER WEIGHT SWEEP SUMMARY")
    print("="*60)
    print(f"{'Config':<15} {'Recall@5':>10} {'MRR':>8} {'single':>8} {'multi':>8} {'temp':>7} {'open':>8}")
    print("-"*60)
    for r in results:
        pc = r['per_category']
        print(f"{r['label']:<15} {str(r['recall_at_5'])+'%':>10} {str(r['mrr']):>8} "
              f"{str(pc.get('single-hop','?'))+'%':>8} "
              f"{str(pc.get('multi-hop','?'))+'%':>8} "
              f"{str(pc.get('temporal','?'))+'%':>7} "
              f"{str(pc.get('open-domain','?'))+'%':>8}")
    print("="*60)
    print(f"\nResults saved to: {RESULTS_FILE}")
    print("SWEEP DONE")

if __name__ == '__main__':
    main()