#!/usr/bin/env python3
"""
Backfill embeddings for notes that have NULL embeddings.
Typically needed after batch import via direct SQLite insert.

Usage (inside Docker):
    python3 /app/scripts/backfill_embeddings.py

Usage (from host, via docker exec):
    docker exec hippograph python3 /app/scripts/backfill_embeddings.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, '/app')  # Docker path

import sqlite3
import numpy as np
import json
from stable_embeddings import StableEmbeddingModel

DB_PATH = os.getenv('DB_PATH', '/app/data/memory.db')

def backfill():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Find notes without embeddings
    cursor.execute('SELECT id, content FROM nodes WHERE embedding IS NULL ORDER BY id')
    missing = cursor.fetchall()
    
    if not missing:
        print("✅ All notes have embeddings. Nothing to do.")
        return
    
    print(f"📊 Found {len(missing)} notes without embeddings")
    
    # Load model
    model = StableEmbeddingModel()
    print(f"🤖 Model loaded, generating embeddings...")
    
    success = 0
    errors = 0
    
    for i, (note_id, content) in enumerate(missing):
        try:
            embedding = model.encode(content)
            blob = np.array(embedding, dtype=np.float32).tobytes()
            cursor.execute('UPDATE nodes SET embedding = ? WHERE id = ?', (blob, note_id))
            success += 1
            
            if (i + 1) % 20 == 0:
                conn.commit()
                print(f"  Progress: {i+1}/{len(missing)} ({success} ok, {errors} errors)")
                
        except Exception as e:
            errors += 1
            print(f"  ❌ Error on note #{note_id}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Backfill complete: {success} embeddings generated, {errors} errors")
    print(f"⚠️  Restart container to rebuild ANN index: docker compose restart hippograph")

if __name__ == '__main__':
    backfill()
