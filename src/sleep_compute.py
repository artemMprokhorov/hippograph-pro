#!/usr/bin/env python3
"""
Sleep-Time Compute — Background graph maintenance daemon.

Runs periodically (default: every 6 hours) and performs:
1. Memory consolidation (thematic clusters + temporal chains)
2. PageRank recalculation
3. Community detection refresh
4. Orphan entity cleanup
5. Stale edge decay

Zero LLM cost — pure graph math via NetworkX.

Usage:
    # Run once
    python3 src/sleep_compute.py --once

    # Run as daemon (every N hours)
    python3 src/sleep_compute.py --interval 6

    # Dry run (report only, no changes)
    python3 src/sleep_compute.py --once --dry-run
"""
import os
import sys
import time
import sqlite3
import argparse
import signal
from datetime import datetime, timedelta

DB_PATH = os.getenv("DB_PATH", "/app/data/memory.db")
STALE_EDGE_DAYS = int(os.getenv("STALE_EDGE_DAYS", "90"))
ORPHAN_MIN_LINKS = int(os.getenv("ORPHAN_MIN_LINKS", "1"))
running = True


def signal_handler(sig, frame):
    global running
    print("\nShutting down gracefully...")
    running = False

# Signal handlers only work in main thread — register conditionally
import threading as _threading
if _threading.current_thread() is _threading.main_thread():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def get_db():
    db = DB_PATH
    if not os.path.exists(db):
        db = os.path.join(os.path.dirname(__file__), "..", "data", "memory.db")
    if not os.path.exists(db):
        print(f"Database not found: {db}")
        sys.exit(1)
    return db


def step_consolidation(db_path, dry_run=False):
    """Step 1: Thematic clusters + temporal chains."""
    from memory_consolidation import run_consolidation
    print("\n=== Step 1: Memory Consolidation ===")
    if dry_run:
        from memory_consolidation import MemoryConsolidator
        c = MemoryConsolidator(db_path)
        clusters = c.find_thematic_clusters()
        chains = c.find_temporal_chains()
        print(f"  Would create links from {len(clusters)} clusters, {len(chains)} chains")
        return {"clusters": len(clusters), "chains": len(chains), "links": 0}
    result = run_consolidation(db_path)
    return result

def step_pagerank(db_path, dry_run=False):
    """Step 2: Recalculate PageRank + communities."""
    print("\n=== Step 2: PageRank + Community Detection ===")
    from graph_metrics import GraphMetrics

    conn = sqlite3.connect(db_path)
    nodes = [r[0] for r in conn.execute("SELECT id FROM nodes").fetchall()]
    edges = conn.execute(
        "SELECT source_id, target_id, weight FROM edges"
    ).fetchall()
    conn.close()

    metrics = GraphMetrics()
    metrics.compute(edges, nodes)

    top_pr = sorted(metrics._pagerank.items(), key=lambda x: x[1], reverse=True)[:10]
    n_communities = len(metrics._community_sizes)
    isolated = sum(1 for v in metrics._communities.values() if v == -1)

    print(f"  Nodes: {len(nodes)}, Edges: {len(edges)}")
    print(f"  Communities: {n_communities}, Isolated: {isolated}")
    print(f"  Top PageRank: {', '.join(f'#{nid}({pr:.3f})' for nid, pr in top_pr[:5])}")
    return {
        "nodes": len(nodes), "edges": len(edges),
        "communities": n_communities, "isolated": isolated
    }


def step_relation_extraction(db_path, dry_run=False, batch_size=20, limit=200):
    """Step 2.5: Deep Sleep — extract typed relations via GLiNER2 and build graph edges."""
    print("\n=== Step 2.5: Relation Extraction (GLiNER2 Deep Sleep) ===")

    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(__file__))
        import gliner2_client
    except ImportError as e:
        print(f"  ⚠️ gliner2_client import failed: {e}")
        return {"skipped": True, "reason": "gliner2_client unavailable"}

    if not gliner2_client.is_available():
        print("  ⚠️ GLiNER2 not available (install: pip install gliner2)")
        return {"skipped": True, "reason": "gliner2 not installed"}

    conn = sqlite3.connect(db_path)

    # Fetch nodes not yet processed by GLiNER2 relation extraction
    # Use access_count and last_accessed as proxy — process oldest/least accessed first
    rows = conn.execute("""
        SELECT id, content FROM nodes
        ORDER BY last_accessed ASC NULLS FIRST
        LIMIT ?
    """, (limit,)).fetchall()

    if not rows:
        print("  No nodes to process.")
        conn.close()
        return {"processed": 0, "relations_found": 0, "edges_created": 0}

    print(f"  Processing {len(rows)} nodes in batches of {batch_size}...")

    # Batch process
    texts = [row[1] for row in rows]
    node_ids = [row[0] for row in rows]

    all_triples = gliner2_client.extract_relations_batch(
        texts, batch_size=batch_size
    )

    # Build entity -> node_id index for matching
    # Use existing entities table to find which nodes contain which entities
    entity_rows = conn.execute("""
        SELECT ne.node_id, e.name, e.entity_type
        FROM node_entities ne
        JOIN entities e ON ne.entity_id = e.id
    """).fetchall()

    # entity_name.lower() -> list of node_ids
    entity_index = {}
    for node_id, name, etype in entity_rows:
        key = name.lower()
        if key not in entity_index:
            entity_index[key] = []
        if node_id not in entity_index[key]:
            entity_index[key].append(node_id)

    # Create edges for found relations
    edges_created = 0
    edges_skipped = 0
    total_relations = 0
    now = datetime.now().isoformat()

    for i, (node_id, triples) in enumerate(zip(node_ids, all_triples)):
        total_relations += len(triples)
        for subject, rel_type, obj in triples:
            # Find nodes that contain these entities
            subject_nodes = entity_index.get(subject.lower(), [])
            object_nodes = entity_index.get(obj.lower(), [])

            # If no entity match, at least link current node to itself (skip)
            if not subject_nodes and not object_nodes:
                edges_skipped += 1
                continue

            # Use current node as source if subject not found elsewhere
            src_nodes = subject_nodes if subject_nodes else [node_id]
            tgt_nodes = object_nodes if object_nodes else [node_id]

            for src in src_nodes[:3]:   # cap to avoid explosion
                for tgt in tgt_nodes[:3]:
                    if src == tgt:
                        continue
                    try:
                        if not dry_run:
                            conn.execute("""
                                INSERT OR IGNORE INTO edges
                                (source_id, target_id, weight, edge_type, created_at)
                                VALUES (?, ?, ?, ?, ?)
                            """, (src, tgt, 0.6, rel_type, now))
                            edges_created += conn.execute(
                                "SELECT changes()"
                            ).fetchone()[0]
                        else:
                            edges_created += 1  # dry run count
                    except Exception as e:
                        print(f"    Edge insert error: {e}")

    if not dry_run:
        conn.commit()
    conn.close()

    print(f"  Nodes processed: {len(rows)}")
    print(f"  Relations found: {total_relations}")
    print(f"  Edges created:   {edges_created}")
    print(f"  Edges skipped (no entity match): {edges_skipped}")
    return {
        "processed": len(rows),
        "relations_found": total_relations,
        "edges_created": edges_created,
        "edges_skipped": edges_skipped
    }


def step_orphan_cleanup(db_path, dry_run=False):
    """Step 3: Find entities with very few connections."""
    print("\n=== Step 3: Orphan Entity Detection ===")
    conn = sqlite3.connect(db_path)

    # Find notes with 0 or 1 edges
    orphans = conn.execute("""
        SELECT n.id, n.category, LENGTH(n.content) as len
        FROM nodes n
        LEFT JOIN (
            SELECT source_id as nid, COUNT(*) as cnt FROM edges GROUP BY source_id
            UNION ALL
            SELECT target_id as nid, COUNT(*) as cnt FROM edges GROUP BY target_id
        ) e ON n.id = e.nid
        GROUP BY n.id
        HAVING COALESCE(SUM(e.cnt), 0) <= ?
    """, (ORPHAN_MIN_LINKS,)).fetchall()

    conn.close()
    print(f"  Found {len(orphans)} orphan notes (<=  {ORPHAN_MIN_LINKS} edges)")
    if orphans:
        for nid, cat, length in orphans[:5]:
            print(f"    #{nid} [{cat}] {length} chars")
        if len(orphans) > 5:
            print(f"    ... and {len(orphans) - 5} more")
    return {"orphans": len(orphans), "details": [(o[0], o[1]) for o in orphans]}

def step_stale_decay(db_path, dry_run=False):
    """Step 4: Decay weight of edges not accessed recently."""
    print("\n=== Step 4: Stale Edge Decay ===")
    cutoff = (datetime.now() - timedelta(days=STALE_EDGE_DAYS)).isoformat()
    conn = sqlite3.connect(db_path)

    # Find old edges with high weight
    stale = conn.execute("""
        SELECT COUNT(*) FROM edges
        WHERE created_at < ? AND weight > 0.3
    """, (cutoff,)).fetchone()[0]

    if dry_run:
        print(f"  Would decay {stale} edges older than {STALE_EDGE_DAYS} days")
        conn.close()
        return {"stale_edges": stale, "decayed": 0}

    # Decay: multiply weight by 0.95 (gentle aging)
    conn.execute("""
        UPDATE edges SET weight = weight * 0.95
        WHERE created_at < ? AND weight > 0.3
    """, (cutoff,))
    affected = conn.total_changes
    conn.commit()
    conn.close()
    print(f"  Decayed {stale} edges (weight *= 0.95)")
    return {"stale_edges": stale, "decayed": stale}


def step_duplicate_scan(db_path, dry_run=False):
    """Step 5: Find near-duplicate notes by embedding similarity."""
    print("\n=== Step 5: Duplicate Scan ===")
    import numpy as np
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT id, embedding FROM nodes WHERE embedding IS NOT NULL"
    ).fetchall()
    conn.close()

    embeddings = {}
    for nid, blob in rows:
        if blob:
            embeddings[nid] = np.frombuffer(blob, dtype=np.float32)

    # Sample-based check (full O(n^2) too slow for large graphs)
    ids = list(embeddings.keys())
    duplicates = []
    checked = 0
    threshold = 0.95

    for i in range(len(ids)):
        for j in range(i + 1, min(i + 50, len(ids))):  # sliding window
            e1, e2 = embeddings[ids[i]], embeddings[ids[j]]
            sim = np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))
            checked += 1
            if sim >= threshold:
                duplicates.append((ids[i], ids[j], float(sim)))

    print(f"  Checked {checked} pairs, found {len(duplicates)} near-duplicates (>{threshold})")
    for a, b, sim in duplicates[:5]:
        print(f"    #{a} <-> #{b} similarity={sim:.4f}")
    return {"checked": checked, "duplicates": len(duplicates), "pairs": duplicates[:20]}

def run_all(db_path, dry_run=False):
    """Run all sleep-time compute steps."""
    t0 = time.time()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"  Sleep-Time Compute — {ts}")
    print(f"  Database: {db_path}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}")

    results = {}
    try:
        results['consolidation'] = step_consolidation(db_path, dry_run)
    except Exception as e:
        print(f"  ERROR in consolidation: {e}")
        results['consolidation'] = {"error": str(e)}

    try:
        results['pagerank'] = step_pagerank(db_path, dry_run)
    except Exception as e:
        print(f"  ERROR in pagerank: {e}")
        results['pagerank'] = {"error": str(e)}

    try:
        results['relation_extraction'] = step_relation_extraction(db_path, dry_run)
    except Exception as e:
        print(f"  ERROR in relation extraction: {e}")
        results['relation_extraction'] = {"error": str(e)}

    try:
        results['orphans'] = step_orphan_cleanup(db_path, dry_run)
    except Exception as e:
        print(f"  ERROR in orphan cleanup: {e}")
        results['orphans'] = {"error": str(e)}

    try:
        results['decay'] = step_stale_decay(db_path, dry_run)
    except Exception as e:
        print(f"  ERROR in stale decay: {e}")
        results['decay'] = {"error": str(e)}

    try:
        results['duplicates'] = step_duplicate_scan(db_path, dry_run)
    except Exception as e:
        print(f"  ERROR in duplicate scan: {e}")
        results['duplicates'] = {"error": str(e)}

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  Completed in {elapsed:.1f}s")
    print(f"{'='*60}\n")
    return results


def main():
    parser = argparse.ArgumentParser(description="Sleep-Time Compute Daemon")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=float, default=6, help="Hours between runs (default: 6)")
    parser.add_argument("--dry-run", action="store_true", help="Report only, no changes")
    parser.add_argument("--db", type=str, default=None, help="Database path override")
    args = parser.parse_args()

    db_path = args.db or get_db()

    if args.once:
        run_all(db_path, dry_run=args.dry_run)
        return

    interval_sec = args.interval * 3600
    print(f"Sleep-Time Compute Daemon started (interval: {args.interval}h)")
    print(f"Database: {db_path}")

    while running:
        run_all(db_path, dry_run=args.dry_run)
        # Sleep in small increments for graceful shutdown
        for _ in range(int(interval_sec / 10)):
            if not running:
                break
            time.sleep(10)

    print("Daemon stopped.")


if __name__ == "__main__":
    main()
