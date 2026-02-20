#!/usr/bin/env python3
"""
Re-index all embeddings after changing EMBEDDING_MODEL.

Usage:
    python3 src/reindex_embeddings.py [--dry-run]

This script:
1. Loads the new embedding model from EMBEDDING_MODEL env var
2. Re-encodes all notes with the new model
3. Updates embeddings in the database
4. Rebuilds the ANN index

BACKUP YOUR DATABASE BEFORE RUNNING THIS SCRIPT!
"""
import os
import sys
import time
import sqlite3
import numpy as np


def main():
    dry_run = "--dry-run" in sys.argv

    db_path = os.getenv("DB_PATH", "/app/data/memory.db")
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(__file__), "..", "data", "memory.db")

    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    from stable_embeddings import StableEmbeddingModel
    model = StableEmbeddingModel()
    new_dim = model.dimension
    print(f"New embedding dimension: {new_dim}")

    conn = sqlite3.connect(db_path)
    total = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    sample = conn.execute(
        "SELECT embedding FROM nodes WHERE embedding IS NOT NULL LIMIT 1"
    ).fetchone()

    if sample and sample[0]:
        old_emb = np.frombuffer(sample[0], dtype=np.float32)
        old_dim = len(old_emb)
        print(f"Current dim: {old_dim}, New dim: {new_dim}, Notes: {total}")
    else:
        print(f"No existing embeddings. Notes: {total}")

    if dry_run:
        print("DRY RUN - no changes made")
        conn.close()
        return

    print(f"\nThis will re-encode {total} notes (~{total * 0.05:.0f}s)")
    print("Make sure you have a backup!")
    response = input("Continue? [y/N]: ")
    if response.lower() != "y":
        print("Aborted.")
        conn.close()
        return

    rows = conn.execute("SELECT id, content FROM nodes ORDER BY id").fetchall()
    t0 = time.perf_counter()
    updated = 0
    errors = 0

    for i, (nid, content) in enumerate(rows):
        try:
            embedding = model.encode(content)
            if isinstance(embedding, np.ndarray) and embedding.ndim > 1:
                embedding = embedding[0]
            conn.execute(
                "UPDATE nodes SET embedding = ? WHERE id = ?",
                (embedding.astype(np.float32).tobytes(), nid)
            )
            updated += 1
            if (i + 1) % 50 == 0:
                conn.commit()
                elapsed = time.perf_counter() - t0
                rate = (i + 1) / elapsed
                remaining = (total - i - 1) / rate
                print(f"  [{i+1}/{total}] {rate:.1f} notes/s, ~{remaining:.0f}s left")
        except Exception as e:
            print(f"  Error note #{nid}: {e}")
            errors += 1

    conn.commit()
    elapsed = time.perf_counter() - t0
    print(f"\nRe-indexed {updated}/{total} notes in {elapsed:.1f}s")
    if errors:
        print(f"  {errors} errors")
    print("Restart server to rebuild ANN index.")
    conn.close()


if __name__ == "__main__":
    main()
