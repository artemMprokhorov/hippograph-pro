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


def step_relation_extraction(db_path, dry_run=False, batch_size=5, limit=20):
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

    # Ensure edge_history table exists for conflict tracking
    conn.execute("""
        CREATE TABLE IF NOT EXISTS edge_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            edge_type TEXT,
            weight REAL,
            conflict_type TEXT,  -- 'new_relation' | 'type_conflict'
            existing_edge_type TEXT,
            created_at TEXT,
            FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES nodes(id) ON DELETE CASCADE
        )
    """)
    conn.commit()

    # Fetch nodes not yet processed by GLiNER2 relation extraction
    # Use access_count and last_accessed as proxy — process oldest/least accessed first
    # Incremental: only nodes added since last sleep run
    conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    last_sleep = conn.execute(
        "SELECT value FROM metadata WHERE key='last_sleep_at' LIMIT 1"
    ).fetchone()
    last_sleep_ts = last_sleep[0] if last_sleep else "1970-01-01"

    rows = conn.execute("""
        SELECT id, content FROM nodes
        WHERE timestamp > ?
        ORDER BY timestamp ASC
        LIMIT ?
    """, (last_sleep_ts, limit)).fetchall()

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
                            # Check if edge already exists with different type
                            existing = conn.execute("""
                                SELECT id, edge_type FROM edges
                                WHERE source_id=? AND target_id=?
                                LIMIT 1
                            """, (src, tgt)).fetchone()

                            if existing:
                                existing_type = existing[1]
                                if existing_type != rel_type:
                                    # Conflict: different relation type found
                                    # Principle: never overwrite existing — log to edge_history
                                    conn.execute("""
                                        INSERT INTO edge_history
                                        (source_id, target_id, edge_type, weight,
                                         conflict_type, existing_edge_type, created_at)
                                        VALUES (?, ?, ?, ?, 'type_conflict', ?, ?)
                                    """, (src, tgt, rel_type, 0.6, existing_type, now))
                                # else: same type, INSERT OR IGNORE handles it silently
                            else:
                                # No existing edge — safe to create
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


def step_spacy_relations(db_path, dry_run=False):
    """Step 2.6: Build typed edges from existing spaCy entity data.

    Covers ALL nodes using already-extracted entity types.
    No LLM, no model loading — pure SQL + entity type rules.
    Runs every sleep cycle as comprehensive pass.

    Relation rules:
      person + organization  -> works_for
      person + location      -> located_in
      person + concept       -> knows_about
      person + tech          -> uses
      tech + tech            -> depends_on
      tech + concept         -> implements
      concept + concept      -> related_to
      organization + location -> located_in
    """
    print("\n=== Step 2.6: spaCy Entity Relations ===")

    RELATION_RULES = {
        ('person', 'organization'): 'works_for',
        ('organization', 'person'): 'works_for',
        ('person', 'location'): 'located_in',
        ('location', 'person'): 'located_in',
        ('person', 'concept'): 'knows_about',
        ('concept', 'person'): 'knows_about',
        ('person', 'tech'): 'uses',
        ('tech', 'person'): 'uses',
        ('tech', 'tech'): 'depends_on',
        ('tech', 'concept'): 'implements',
        ('concept', 'tech'): 'implements',
        ('concept', 'concept'): 'related_to',
        ('organization', 'location'): 'located_in',
        ('location', 'organization'): 'located_in',
        ('organization', 'tech'): 'uses',
        ('tech', 'organization'): 'uses',
    }

    conn = sqlite3.connect(db_path)

    # For each node: get all entity types present
    node_entity_types = {}
    rows = conn.execute("""
        SELECT ne.node_id, e.entity_type
        FROM node_entities ne
        JOIN entities e ON ne.entity_id = e.id
        WHERE e.entity_type IS NOT NULL
    """).fetchall()

    for node_id, etype in rows:
        if node_id not in node_entity_types:
            node_entity_types[node_id] = set()
        node_entity_types[node_id].add(etype)

    print(f"  Nodes with entities: {len(node_entity_types)}")

    # For each pair of entity types within same node -> create edge via
    # shared entity to other nodes that have that entity
    # Simpler: for each node with 2+ entity types, find other nodes sharing
    # at least one entity, then apply type rules between the node pairs.

    # Build entity_id -> list of (node_id, entity_type)
    entity_nodes = {}
    entity_type_map = {}
    full_rows = conn.execute("""
        SELECT ne.node_id, ne.entity_id, e.entity_type
        FROM node_entities ne
        JOIN entities e ON ne.entity_id = e.id
        WHERE e.entity_type IS NOT NULL
    """).fetchall()

    for node_id, eid, etype in full_rows:
        if eid not in entity_nodes:
            entity_nodes[eid] = []
        entity_nodes[eid].append((node_id, etype))
        entity_type_map[eid] = etype

    edges_created = 0
    edges_checked = 0
    now = datetime.now().isoformat()

    # For each entity shared by multiple nodes: pair up nodes and apply rules
    for eid, node_list in entity_nodes.items():
        if len(node_list) < 2:
            continue
        etype = entity_type_map[eid]

        for i in range(len(node_list)):
            for j in range(i + 1, len(node_list)):
                src_id, src_type = node_list[i]
                tgt_id, tgt_type = node_list[j]

                if src_id == tgt_id:
                    continue

                # Check rule for this type pair
                rel_type = RELATION_RULES.get((src_type, tgt_type))
                if rel_type is None:
                    rel_type = RELATION_RULES.get((tgt_type, src_type))
                if rel_type is None:
                    rel_type = 'related_to'  # fallback

                edges_checked += 1

                if not dry_run:
                    existing = conn.execute("""
                        SELECT id FROM edges
                        WHERE source_id=? AND target_id=?
                        LIMIT 1
                    """, (src_id, tgt_id)).fetchone()

                    if not existing:
                        conn.execute("""
                            INSERT OR IGNORE INTO edges
                            (source_id, target_id, weight, edge_type, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (src_id, tgt_id, 0.5, rel_type, now))
                        edges_created += conn.execute("SELECT changes()").fetchone()[0]
                else:
                    edges_created += 1

    if not dry_run:
        conn.commit()
    conn.close()

    print(f"  Entity pairs checked: {edges_checked}")
    print(f"  Edges {'would be ' if dry_run else ''}created: {edges_created}")
    return {"checked": edges_checked, "edges_created": edges_created}

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

# Categories protected from stale edge decay
PROTECTED_CATEGORIES = {
    "anchor", "self-reflection", "relational-context",
    "gratitude", "milestone", "protocol", "security", "breakthrough"
}


def step_stale_decay(db_path, dry_run=False):
    """Step 4: Decay weight of edges not accessed recently.
    
    Anchor Memory protection: edges connected to protected category nodes
    are exempt from decay to preserve identity and relational memory.
    """
    print("\n=== Step 4: Stale Edge Decay ===")
    cutoff = (datetime.now() - timedelta(days=STALE_EDGE_DAYS)).isoformat()
    conn = sqlite3.connect(db_path)

    # Count all stale edges
    stale_all = conn.execute("""
        SELECT COUNT(*) FROM edges
        WHERE created_at < ? AND weight > 0.3
    """, (cutoff,)).fetchone()[0]

    # Count protected edges (connected to anchor/protected nodes)
    protected = conn.execute("""
        SELECT COUNT(*) FROM edges e
        WHERE e.created_at < ? AND e.weight > 0.3
          AND (
            EXISTS (SELECT 1 FROM nodes n WHERE n.id = e.source_id AND n.category IN ({}))
            OR
            EXISTS (SELECT 1 FROM nodes n WHERE n.id = e.target_id AND n.category IN ({}))
          )
    """.format(
        ",".join("?" * len(PROTECTED_CATEGORIES)),
        ",".join("?" * len(PROTECTED_CATEGORIES))
    ), [cutoff] + list(PROTECTED_CATEGORIES) + list(PROTECTED_CATEGORIES)).fetchone()[0]

    stale_decay = stale_all - protected
    print(f"  Stale edges: {stale_all} total, {protected} protected (anchor), {stale_decay} to decay")

    if dry_run:
        conn.close()
        return {"stale_edges": stale_all, "protected": protected, "decayed": 0}

    # Decay only non-protected edges
    conn.execute("""
        UPDATE edges SET weight = weight * 0.95
        WHERE created_at < ? AND weight > 0.3
          AND NOT (
            EXISTS (SELECT 1 FROM nodes n WHERE n.id = source_id AND n.category IN ({}))
            OR
            EXISTS (SELECT 1 FROM nodes n WHERE n.id = target_id AND n.category IN ({}))
          )
    """.format(
        ",".join("?" * len(PROTECTED_CATEGORIES)),
        ",".join("?" * len(PROTECTED_CATEGORIES))
    ), [cutoff] + list(PROTECTED_CATEGORIES) + list(PROTECTED_CATEGORIES))

    conn.commit()
    conn.close()
    print(f"  Decayed {stale_decay} edges (weight *= 0.95), protected {protected} anchor edges")
    return {"stale_edges": stale_all, "protected": protected, "decayed": stale_decay}


def step_boost_anchor_importance(db_path, dry_run=False):
    """Step 4b: Ensure anchor/protected notes maintain critical importance.
    
    Sleep compute should reinforce anchor nodes, not let them fade.
    If a protected category note has importance != critical, upgrade it.
    """
    print("\n=== Step 4b: Anchor Importance Boost ===")
    conn = sqlite3.connect(db_path)

    # Find protected notes that aren't critical
    candidates = conn.execute("""
        SELECT id, category, importance FROM nodes
        WHERE category IN ({})
          AND importance != 'critical'
    """.format(",".join("?" * len(PROTECTED_CATEGORIES))),
    list(PROTECTED_CATEGORIES)).fetchall()

    print(f"  Found {len(candidates)} anchor notes below critical importance")

    if dry_run or not candidates:
        conn.close()
        return {"boosted": 0, "candidates": len(candidates)}

    ids = [row[0] for row in candidates]
    conn.execute("""
        UPDATE nodes SET importance = 'critical'
        WHERE id IN ({})
    """.format(",".join("?" * len(ids))), ids)

    conn.commit()
    conn.close()
    print(f"  Boosted {len(candidates)} anchor notes to critical importance")
    return {"boosted": len(candidates), "candidates": len(candidates)}


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

SNAPSHOT_DIR = os.getenv("SNAPSHOT_DIR", "/app/data/snapshots")
MAX_SNAPSHOTS = int(os.getenv("MAX_SNAPSHOTS", "7"))  # Keep last 7 snapshots


def create_snapshot(db_path):
    """Create a timestamped snapshot of the database before sleep compute.
    
    Returns snapshot path on success, None on failure.
    Safety principle: never modify original DB without a snapshot.
    """
    import shutil
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_path = os.path.join(SNAPSHOT_DIR, f"memory_snapshot_{ts}.db")
    try:
        shutil.copy2(db_path, snapshot_path)
        print(f"  Snapshot created: {snapshot_path}")
        # Prune old snapshots — keep last MAX_SNAPSHOTS
        snapshots = sorted([
            os.path.join(SNAPSHOT_DIR, f) for f in os.listdir(SNAPSHOT_DIR)
            if f.startswith("memory_snapshot_") and f.endswith(".db")
        ])
        while len(snapshots) > MAX_SNAPSHOTS:
            old_snap = snapshots.pop(0)
            os.remove(old_snap)
            print(f"  Pruned old snapshot: {old_snap}")
        return snapshot_path
    except Exception as e:
        print(f"  WARNING: Could not create snapshot: {e}")
        return None


def restore_snapshot(snapshot_path, db_path):
    """Restore database from snapshot.
    
    Only called on explicit error — never as "optimization".
    """
    import shutil
    try:
        shutil.copy2(snapshot_path, db_path)
        print(f"  Restored from snapshot: {snapshot_path}")
        return True
    except Exception as e:
        print(f"  ERROR: Could not restore snapshot: {e}")
        return False


def run_all(db_path, dry_run=False):
    """Run all sleep-time compute steps."""
    t0 = time.time()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"  Sleep-Time Compute — {ts}")
    print(f"  Database: {db_path}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}")

    # Safety: create snapshot before any changes
    snapshot_path = None
    if not dry_run:
        snapshot_path = create_snapshot(db_path)
        if snapshot_path is None:
            print("  WARNING: Proceeding without snapshot — backup manually if concerned")

    results = {"snapshot": snapshot_path}
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
        results['spacy_relations'] = step_spacy_relations(db_path, dry_run)
    except Exception as e:
        print(f"  ERROR in spacy relations: {e}")
        results['spacy_relations'] = {"error": str(e)}

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
        results['anchor_boost'] = step_boost_anchor_importance(db_path, dry_run)
    except Exception as e:
        print(f"  ERROR in anchor boost: {e}")
        results['anchor_boost'] = {"error": str(e)}

    try:
        results['duplicates'] = step_duplicate_scan(db_path, dry_run)
    except Exception as e:
        print(f"  ERROR in duplicate scan: {e}")
        results['duplicates'] = {"error": str(e)}

    # Update last_sleep_at timestamp
    if not dry_run:
        try:
            conn2 = __import__('sqlite3').connect(db_path)
            conn2.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
            conn2.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('last_sleep_at', ?)",
                         [__import__('datetime').datetime.now().isoformat()])
            conn2.commit()
            conn2.close()
        except Exception as e:
            print(f"  WARNING: Could not update last_sleep_at: {e}")

    # Also add spacy_relations step to run_all results
    elapsed = time.time() - t0

    # Rollback check: if any critical step had an error AND snapshot exists,
    # offer rollback. We NEVER auto-rollback — human decides.
    # Principle: errors in individual steps are logged, not auto-reverted.
    # Only catastrophic DB corruption warrants rollback.
    critical_errors = [
        k for k in ('consolidation', 'relation_extraction', 'decay', 'anchor_boost')
        if isinstance(results.get(k), dict) and 'error' in results[k]
    ]
    if critical_errors and snapshot_path:
        print(f"\n  ⚠️  Errors in steps: {critical_errors}")
        print(f"  Snapshot available for manual rollback:")
        restore_cmd = f"from sleep_compute import restore_snapshot; restore_snapshot(\'{snapshot_path}\', \'{db_path}\')"
        print(f"    python3 -c \"{restore_cmd}\"")
        results['rollback_available'] = snapshot_path
    elif snapshot_path:
        results['rollback_available'] = snapshot_path

    print(f"\n{'='*60}")
    print(f"  Completed in {elapsed:.1f}s")
    if snapshot_path:
        print(f"  Snapshot: {os.path.basename(snapshot_path)}")
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
