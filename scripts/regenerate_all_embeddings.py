#!/usr/bin/env python3
"""
Regenerate ALL embeddings with new model.
Usage: docker exec hippograph python3 /app/scripts/regenerate_all_embeddings.py
"""
import sqlite3
import sys
import os
import numpy as np

sys.path.insert(0, '/app/src')
from stable_embeddings import get_model

DB_PATH = os.getenv('DB_PATH', '/app/data/memory.db')

def main():
    model = get_model()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, content FROM nodes ORDER BY id")
    nodes = cursor.fetchall()
    total = len(nodes)
    print(f"Regenerating embeddings for {total} nodes...")
    
    success = 0
    errors = 0
    batch_size = 20
    
    for i, node in enumerate(nodes):
        try:
            emb = model.encode(node['content']).flatten()
            cursor.execute(
                "UPDATE nodes SET embedding = ? WHERE id = ?",
                (emb.astype(np.float32).tobytes(), node['id'])
            )
            success += 1
            if (i + 1) % batch_size == 0:
                conn.commit()
                print(f"  [{i+1}/{total}] {success} ok, {errors} errors")
                
        except Exception as e:
            errors += 1
            print(f"  ERROR node {node['id']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Done: {success}/{total} embeddings regenerated, {errors} errors")
    print(f"Model: {os.getenv('EMBEDDING_MODEL', 'default')}")
    print("⚠️  Restart container to rebuild ANN index!")

if __name__ == '__main__':
    main()
