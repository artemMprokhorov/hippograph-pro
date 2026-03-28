import sys, os
sys.path.insert(0, '/app/src')
sys.path.insert(0, '/app/benchmark')
os.environ.setdefault('DB_PATH', '/app/data/benchmark.db')
from locomo_adapter import parse_dataset, load_into_hippograph, evaluate_retrieval
print('Benchmark #40: Online Consolidation')
print('Loading LOCOMO...')
conversations, qa_pairs = parse_dataset()
load_into_hippograph(conversations, 'http://localhost:5000', 'benchmark_key_locomo_2026', 'turn')
print('Running search...')
evaluate_retrieval(qa_pairs, conversations, 'http://localhost:5000', 'benchmark_key_locomo_2026')
print('DONE')