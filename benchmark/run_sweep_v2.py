#!/usr/bin/env python3
"""
Sweep runner v2 — uses Python subprocess for docker run/stop/rm.
Passes env vars correctly without bash eval issues.

Usage:
  python3 run_sweep_v2.py reranker
  python3 run_sweep_v2.py blend
  python3 run_sweep_v2.py ann_topk
"""

import subprocess, sys, time, os, sqlite3
from datetime import datetime

SWEEP = sys.argv[1] if len(sys.argv) > 1 else None
if not SWEEP:
    print("Usage: python3 run_sweep_v2.py reranker|blend|ann_topk")
    sys.exit(1)

CONTAINER = "hippograph-locomo"
IMAGE = "hippograph-pro-hippograph-locomo"
RESULTS_DIR = "/Volumes/Balances/hippograph-pro/benchmark/results"
API_KEY = "locomo_key_2026"
DB_PATH = "/Volumes/Balances/hippograph-pro/data/benchmark/locomo_test.db"

BASE_ENV = {
    "DB_PATH": "/app/data/locomo_test.db",
    "FLASK_PORT": "5000",
    "FLASK_DEBUG": "false",
    "NEURAL_API_KEY": "locomo_key_2026",
    "ACTIVATION_ITERATIONS": "3",
    "ACTIVATION_DECAY": "0.7",
    "SIMILARITY_THRESHOLD": "0.5",
    "HALF_LIFE_DAYS": "30",
    "ENTITY_EXTRACTOR": "spacy",
    "EMBEDDING_MODEL": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "USE_ANN_INDEX": "true",
    "ANN_INDEX_TYPE": "HNSW",
    "HNSW_M": "32",
    "HNSW_EF_CONSTRUCTION": "64",
    "HNSW_EF_SEARCH": "32",
    "SLEEP_ENABLED": "false",
    "SLEEP_NOTE_THRESHOLD": "999999",
    "DEEP_SLEEP_ENABLED": "false",
    "DISABLE_CATEGORY_DECAY": "true",
    "RERANK_ENABLED": "true",
    "RERANK_TOP_N": "20",
    "RERANK_WEIGHT": "0.8",  # optimized
    "BLEND_ALPHA": "0.6",
    "BLEND_GAMMA": "0.15",
    "BLEND_DELTA": "0.1",
}

BASE_VOLUMES = [
    "/Volumes/Balances/hippograph-pro/data/benchmark:/app/data",
    "/Volumes/Balances/hippograph-pro/src:/app/src",
    "/Volumes/Balances/hippograph-pro/benchmark:/app/benchmark",
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def run(cmd, check=False):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r

def stop_container():
    run(["docker", "stop", CONTAINER])
    run(["docker", "rm", CONTAINER])
    time.sleep(2)

def start_container(extra_env: dict):
    env = {**BASE_ENV, **extra_env}
    cmd = ["docker", "run", "-d", "--name", CONTAINER,
           "--health-cmd", "curl -f http://localhost:5000/health",
           "--health-interval", "15s",
           "--health-retries", "5",
           "-p", "5004:5000"]
    for v in BASE_VOLUMES:
        cmd += ["-v", v]
    for k, v in env.items():
        cmd += ["-e", f"{k}={v}"]
    cmd.append(IMAGE)
    r = run(cmd)
    if r.returncode != 0:
        log(f"ERROR starting container: {r.stderr}")
        return False
    # Wait for healthy
    for i in range(24):  # up to 120s
        time.sleep(5)
        r = run(["docker", "inspect", CONTAINER, "--format", "{{.State.Health.Status}}"])
        status = r.stdout.strip()
        log(f"  Health: {status} ({(i+1)*5}s)")
        if status == "healthy":
            return True
    log("WARNING: not healthy after 120s, proceeding")
    return True

def clear_db():
    conn = sqlite3.connect(DB_PATH)
    for t in ['nodes','edges','entities','node_entities']:
        conn.execute(f'DELETE FROM {t}')
    conn.commit()
    n = conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0]
    conn.close()
    log(f"DB cleared: {n} nodes")

def parse_results(stdout):
    recall = mrr = None
    per_cat = {}
    in_results = False
    for line in stdout.split('\n'):
        if 'LOCOMO BENCHMARK RESULTS' in line:
            in_results = True
        if in_results and 'Recall@5:' in line and '%' in line and '(' in line \
                and not any(c in line for c in ['single','multi','temporal','open']):
            try: recall = float(line.split('Recall@5:')[1].split('%')[0].strip())
            except: pass
        if in_results and line.strip().startswith('MRR:'):
            try: mrr = float(line.split('MRR:')[1].strip())
            except: pass
        for cat in ['single-hop','multi-hop','temporal','open-domain']:
            if in_results and cat in line and 'Recall@5=' in line:
                try: per_cat[cat] = float(line.split('Recall@5=')[1].split('%')[0].strip())
                except: pass
    return recall, mrr, per_cat

def run_config(label, extra_env, chunk=3):
    log(f"\n{'='*50}")
    log(f"Config: {label}")
    log(f"Extra env: {extra_env}")
    log(f"{'='*50}")

    stop_container()
    start_container(extra_env)
    clear_db()

    log("Running benchmark...")
    log_file = f"{RESULTS_DIR}/sweep_{SWEEP}_{label}.log"
    r = subprocess.run(
        ["docker", "exec",
         "-e", f"LOCOMO_CHUNK_SIZE={chunk}",
         "-e", "DISABLE_CATEGORY_DECAY=true",
         CONTAINER,
         "python3", "/app/benchmark/locomo_adapter.py", "--all",
         "--api-url", "http://localhost:5000",
         "--api-key", API_KEY,
         "--granularity", "hybrid"],
        capture_output=True, text=True
    )
    with open(log_file, 'w') as f:
        f.write(r.stdout)
        if r.stderr: f.write('\nSTDERR:\n' + r.stderr)

    recall, mrr, per_cat = parse_results(r.stdout)
    log(f"Result: Recall@5={recall}%, MRR={mrr}")
    log(f"Per cat: {per_cat}")

    csv_line = f"{label},{recall},{mrr}"
    with open(f"{RESULTS_DIR}/sweep_{SWEEP}_summary.csv", 'a') as f:
        f.write(csv_line + '\n')
    return recall, mrr, per_cat

# Initialize CSV
with open(f"{RESULTS_DIR}/sweep_{SWEEP}_summary.csv", 'w') as f:
    f.write("label,recall_at_5,mrr\n")

results = []

if SWEEP == 'reranker':
    log("=== RERANKER WEIGHT SWEEP ===")
    configs = [
        ("no_rerank",  {"RERANK_ENABLED": "false"}),
        ("weight_0.2", {"RERANK_WEIGHT": "0.2"}),
        ("weight_0.3", {"RERANK_WEIGHT": "0.3"}),
        ("weight_0.4", {"RERANK_WEIGHT": "0.4"}),
        ("weight_0.5", {"RERANK_WEIGHT": "0.5"}),
        ("weight_0.6", {"RERANK_WEIGHT": "0.6"}),
    ]
elif SWEEP == 'blend':
    log("=== BLEND WEIGHTS SWEEP ===")
    configs = [
        ("a0.5_g0.10", {"BLEND_ALPHA": "0.5", "BLEND_GAMMA": "0.10"}),
        ("a0.5_g0.15", {"BLEND_ALPHA": "0.5", "BLEND_GAMMA": "0.15"}),
        ("a0.5_g0.20", {"BLEND_ALPHA": "0.5", "BLEND_GAMMA": "0.20"}),
        ("a0.6_g0.10", {"BLEND_ALPHA": "0.6", "BLEND_GAMMA": "0.10"}),
        ("a0.6_g0.15", {"BLEND_ALPHA": "0.6", "BLEND_GAMMA": "0.15"}),
        ("a0.6_g0.20", {"BLEND_ALPHA": "0.6", "BLEND_GAMMA": "0.20"}),
        ("a0.7_g0.10", {"BLEND_ALPHA": "0.7", "BLEND_GAMMA": "0.10"}),
        ("a0.7_g0.15", {"BLEND_ALPHA": "0.7", "BLEND_GAMMA": "0.15"}),
        ("a0.8_g0.10", {"BLEND_ALPHA": "0.8", "BLEND_GAMMA": "0.10"}),
    ]
elif SWEEP == 'reranker_high':
    log("=== RERANKER HIGH WEIGHT SWEEP ===(0.7-0.9)")
    configs = [
        ("weight_0.7", {"RERANK_WEIGHT": "0.7"}),
        ("weight_0.8", {"RERANK_WEIGHT": "0.8"}),
        ("weight_0.9", {"RERANK_WEIGHT": "0.9"}),
    ]
elif SWEEP == 'ann_topk':
    log("=== ANN TOP-K SWEEP ===")
    configs = [(f"topk_{k}", {"ANN_TOP_K": str(k)}) for k in [5, 10, 15, 20, 30, 50]]
else:
    print(f"Unknown sweep: {SWEEP}")
    sys.exit(1)

for label, extra_env in configs:
    recall, mrr, per_cat = run_config(label, extra_env)
    results.append((label, recall, mrr))

log("\n" + "="*60)
log(f"SWEEP DONE: {SWEEP}")
log("="*60)
print(f"\n{'label':<16} {'Recall@5':>10} {'MRR':>8}")
print("-"*36)
for label, recall, mrr in results:
    print(f"{label:<16} {str(recall)+'%':>10} {str(mrr):>8}")