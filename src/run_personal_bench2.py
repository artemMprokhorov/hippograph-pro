#!/usr/bin/env python3
"""Personal Continuity Benchmark via direct graph_engine with ANN initialized."""
import sys, os
sys.path.insert(0, '/app/src')
sys.path.insert(0, '/app/benchmark')
os.environ.setdefault('DB_PATH', '/app/data/memory.db')

# Initialize ANN index before importing benchmark
print('Initializing ANN index...')
import sqlite3
from ann_index import rebuild_index, get_ann_index
from stable_embeddings import get_model

db_path = os.environ['DB_PATH']
conn = sqlite3.connect(db_path)
nodes = conn.execute('SELECT id, embedding FROM nodes WHERE embedding IS NOT NULL').fetchall()
conn.close()
nodes_list = [{'id': n[0], 'embedding': n[1]} for n in nodes if n[1]]
count = rebuild_index(nodes_list)
print(f'ANN built: {count} vectors')

# Now run benchmark
from personal_continuity import run_benchmark
run_benchmark()