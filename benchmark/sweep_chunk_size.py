#!/usr/bin/env python3
"""
Chunk size sweep: test CHUNK_SIZE = 2, 3, 4, 5, 8
Clears DB between runs, logs results to sweep_results.json
"""

import subprocess, json, sqlite3, time, sys, os

API_URL = "http://localhost:5000"
API_KEY = "locomo_key_2026"
DB_PATH = "/app/data/locomo_test.db"
RESULTS_FILE = "/app/benchmark/results/sweep_chunk_size.json"

CHUNK_SIZES = [2, 3, 4, 5, 8]

def clear_db():
    conn = sqlite3.connect(DB_PATH)
    for t in ['nodes','edges','entities','node_entities']:
        conn.execute(f'DELETE FROM {t}')
    conn.commit()
    conn.close()
    print("  DB cleared")

def run_benchmark(chunk_size):
    print(f"\n{'='*50}")
    print(f"CHUNK_SIZE = {chunk_size}")
    print(f"{'='*50}")

    clear_db()
    time.sleep(2)  # let server settle

    log_file = f"/app/benchmark/results/sweep_chunk_{chunk_size}.log"
    env = os.environ.copy()
    env['LOCOMO_CHUNK_SIZE'] = str(chunk_size)
    env['DISABLE_CATEGORY_DECAY'] = 'true'

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

    # Parse results from log
    recall = mrr = None
    per_cat = {}
    for line in result.stdout.split('\n'):
        if 'Recall@5:' in line and 'Overall' not in line and 'single' not in line and 'multi' not in line and 'temporal' not in line and 'open' not in line:
            try:
                recall = float(line.split('Recall@5:')[1].split('%')[0].strip())
                mrr_part = line.split('MRR:')[1].strip() if 'MRR:' in line else None
                if mrr_part:
                    mrr = float(mrr_part)
            except:
                pass
        if 'Recall@5:' in line and '%' in line:
            for cat in ['single-hop', 'multi-hop', 'temporal', 'open-domain']:
                if cat in line:
                    try:
                        per_cat[cat] = float(line.split('Recall@5=')[1].split('%')[0].strip())
                    except:
                        pass

    # More robust parsing from last results block
    lines = result.stdout.split('\n')
    in_results = False
    for line in lines:
        if 'LOCOMO BENCHMARK RESULTS' in line:
            in_results = True
        if in_results and 'Recall@5:' in line and '%' in line and '(' in line:
            try:
                recall = float(line.split('Recall@5:')[1].split('%')[0].strip())
            except:
                pass
        if in_results and 'MRR:' in line and 'Recall' not in line:
            try:
                mrr = float(line.split('MRR:')[1].strip())
            except:
                pass
        for cat in ['single-hop', 'multi-hop', 'temporal', 'open-domain']:
            if in_results and cat in line and 'Recall@5=' in line:
                try:
                    per_cat[cat] = float(line.split('Recall@5=')[1].split('%')[0].strip())
                except:
                    pass

    return {
        'chunk_size': chunk_size,
        'recall_at_5': recall,
        'mrr': mrr,
        'per_category': per_cat,
        'log': log_file
    }

def main():
    results = []
    for chunk_size in CHUNK_SIZES:
        r = run_benchmark(chunk_size)
        results.append(r)
        print(f"  Result: Recall@5={r['recall_at_5']}%, MRR={r['mrr']}")
        # Save after each run
        with open(RESULTS_FILE, 'w') as f:
            json.dump(results, f, indent=2)

    print("\n" + "="*60)
    print("CHUNK SIZE SWEEP SUMMARY")
    print("="*60)
    print(f"{'Chunk':>6} {'Recall@5':>10} {'MRR':>8} {'single':>8} {'multi':>8} {'temp':>7} {'open':>8}")
    print("-"*60)
    for r in results:
        pc = r['per_category']
        print(f"{r['chunk_size']:>6} {str(r['recall_at_5'])+'%':>10} {str(r['mrr']):>8} "
              f"{str(pc.get('single-hop','?'))+'%':>8} "
              f"{str(pc.get('multi-hop','?'))+'%':>8} "
              f"{str(pc.get('temporal','?'))+'%':>7} "
              f"{str(pc.get('open-domain','?'))+'%':>8}")
    print("="*60)
    print(f"\nResults saved to: {RESULTS_FILE}")
    print("SWEEP DONE")

if __name__ == '__main__':
    main()