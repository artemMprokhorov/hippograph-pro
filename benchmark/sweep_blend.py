#!/usr/bin/env python3
"""
Blend weights sweep: test combinations of alpha (semantic) and gamma (BM25)
beta = spreading activation = 1 - alpha - gamma - delta
delta fixed at 0.1 (temporal)
"""

import subprocess, json, sqlite3, time, os

API_URL = "http://localhost:5000"
API_KEY = "locomo_key_2026"
DB_PATH = "/app/data/locomo_test.db"
RESULTS_FILE = "/app/benchmark/results/sweep_blend.json"
CHUNK_SIZE = "3"
DELTA = 0.1  # temporal, fixed

# Grid: alpha x gamma, beta = 1 - alpha - gamma - delta
# Only valid combos where beta >= 0
CONFIGS = [
    # label              alpha  gamma  => beta
    ("a0.5_g0.10",       0.5,   0.10),  # beta=0.30
    ("a0.5_g0.15",       0.5,   0.15),  # beta=0.25
    ("a0.5_g0.20",       0.5,   0.20),  # beta=0.20
    ("a0.6_g0.10",       0.6,   0.10),  # beta=0.20
    ("a0.6_g0.15",       0.6,   0.15),  # beta=0.15 — baseline
    ("a0.6_g0.20",       0.6,   0.20),  # beta=0.10
    ("a0.7_g0.10",       0.7,   0.10),  # beta=0.10
    ("a0.7_g0.15",       0.7,   0.15),  # beta=0.05
    ("a0.8_g0.10",       0.8,   0.10),  # beta=0.00 (pure semantic+BM25)
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

def run_benchmark(label, alpha, gamma):
    beta = round(1.0 - alpha - gamma - DELTA, 3)
    print(f"\n{'='*50}")
    print(f"Config: {label} (alpha={alpha}, gamma={gamma}, beta={beta}, delta={DELTA})")
    print(f"{'='*50}")

    if beta < 0:
        print("  SKIP: beta < 0")
        return None

    clear_db()
    time.sleep(2)

    env = os.environ.copy()
    env['LOCOMO_CHUNK_SIZE'] = CHUNK_SIZE
    env['DISABLE_CATEGORY_DECAY'] = 'true'
    env['BLEND_ALPHA'] = str(alpha)
    env['BLEND_GAMMA'] = str(gamma)
    env['BLEND_DELTA'] = str(DELTA)

    log_file = f"/app/benchmark/results/sweep_blend_{label}.log"
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
    return {'label': label, 'alpha': alpha, 'gamma': gamma, 'beta': beta, 'delta': DELTA,
            'recall_at_5': recall, 'mrr': mrr, 'per_category': per_cat, 'log': log_file}

def main():
    results = []
    for label, alpha, gamma in CONFIGS:
        r = run_benchmark(label, alpha, gamma)
        if r:
            results.append(r)
            print(f"  Result: Recall@5={r['recall_at_5']}%, MRR={r['mrr']}")
            with open(RESULTS_FILE, 'w') as f:
                json.dump(results, f, indent=2)

    print("\n" + "="*60)
    print("BLEND WEIGHTS SWEEP SUMMARY")
    print("="*60)
    print(f"{'Config':<16} {'α':>5} {'γ':>5} {'β':>5} {'Recall@5':>10} {'MRR':>8}")
    print("-"*60)
    best = max(results, key=lambda x: x['recall_at_5'] or 0)
    for r in sorted(results, key=lambda x: x['recall_at_5'] or 0, reverse=True):
        marker = " ←BEST" if r == best else ""
        print(f"{r['label']:<16} {r['alpha']:>5} {r['gamma']:>5} {r['beta']:>5} "
              f"{str(r['recall_at_5'])+'%':>10} {str(r['mrr']):>8}{marker}")
    print("="*60)
    print(f"\nResults saved to: {RESULTS_FILE}")
    print("SWEEP DONE")

if __name__ == '__main__':
    main()