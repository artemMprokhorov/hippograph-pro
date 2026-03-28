import sys, os
sys.path.insert(0, '/app/src')
sys.path.insert(0, '/app/benchmark')
os.environ.setdefault('DB_PATH', '/app/data/benchmark.db')
from locomo_adapter import parse_dataset, load_into_hippograph, evaluate_retrieval
from sleep_compute import step_entity_merge
print('Benchmark Phase 2: #40 Online Consolidation + #46 Concept Merging')
print('Loading LOCOMO...')
conversations, qa_pairs = parse_dataset()
load_into_hippograph(conversations, 'http://localhost:5000', 'benchmark_key_locomo_2026', 'turn')
print('Running entity merge...')
step_entity_merge('/app/data/benchmark.db', dry_run=False)
print('Running search queries...')
evaluate_retrieval(qa_pairs, conversations, 'http://localhost:5000', 'benchmark_key_locomo_2026')
print('DONE')