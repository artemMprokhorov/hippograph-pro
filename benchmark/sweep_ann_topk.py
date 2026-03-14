#!/usr/bin/env python3
"""
ANN top-K sweep: test how many ANN seed candidates feed into spreading activation
Patches ANN_TOP_K env var read in graph_engine.py search function
"""

import subprocess, json, sqlite3, time, os

API_URL = "http://localhost:5000"
API_KEY = "locomo_key_2026"
DB_PATH = "/app/data/locomo_test.db"
RESULTS_FILE = "/app/benchmark/results/sweep_ann_topk.json"
CHUNK_SIZE = "3"

# ANN_TOP_K controls how many nearest neighbors seed spreading activation
# Default: MAX_SEMANTIC_LINKS*2 = 10
TOP_K_VALUES = [5, 10, 15, 20, 30, 50]

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

def run_benchmark(top_k):
    print(f"\n{'='*50}")
    print(f"ANN_TOP_K = {top_k}")
    print(f"{'='*50}")

    clear_db()
    time.sleep(2)

    env = os.environ.copy()
    env['LOCOMO_CHUNK_SIZE'] = CHUNK_SIZE
    env['DISABLE_CATEGORY_DECAY'] = 'true'
    env['ANN_TOP_K'] = str(top_k)

    log_file = f"/app/benchmark/results/sweep_ann_topk_{top_k}.log"
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
    return {'top_k': top_k, 'recall_at_5': recall, 'mrr': mrr, 'per_category': per_cat, 'log': log_file}

def main():
    results = []
    for top_k in TOP_K_VALUES:
        r = run_benchmark(top_k)
        results.append(r)
        print(f"  Result: Recall@5={r['recall_at_5']}%, MRR={r['mrr']}")
        with open(RESULTS_FILE, 'w') as f:
            json.dump(results, f, indent=2)

    print("\n" + "="*60)
    print("ANN TOP-K SWEEP SUMMARY")
    print("="*60)
    print(f"{'top_k':>8} {'Recall@5':>10} {'MRR':>8} {'single':>8} {'multi':>8} {'temp':>7} {'open':>8}")
    print("-"*60)
    for r in sorted(results, key=lambda x: x['recall_at_5'] or 0, reverse=True):
        pc = r['per_category']
        print(f"{r['top_k']:>8} {str(r['recall_at_5'])+'%':>10} {str(r['mrr']):>8} "
              f"{str(pc.get('single-hop','?'))+'%':>8} "
              f"{str(pc.get('multi-hop','?'))+'%':>8} "
              f"{str(pc.get('temporal','?'))+'%':>7} "
              f"{str(pc.get('open-domain','?'))+'%':>8}")
    print("="*60)
    print(f"\nResults saved to: {RESULTS_FILE}")
    print("SWEEP DONE")

if __name__ == '__main__':
    main()