#!/usr/bin/env python3
"""
Timestamp-based Temporal Edges v2 -- 100% node coverage.

Difference from v1:
- v1: only nodes with t_event_start (~6% coverage)
- v2: ALL nodes by timestamp (100% coverage)
  Priority: t_event_start > timestamp

DB_PATH: pass via env variable.
"""

import sqlite3
import os

DB_PATH = os.environ.get('DB_PATH', '/app/data/memory_timestamp_exp.db')
NEIGHBORS = 3
WEIGHT = 0.4


def get_connection(db_path):
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def get_effective_time(node):
    """Priority: t_event_start > timestamp."""
    return node['t_event_start'] if node['t_event_start'] else node['timestamp']


def main():
    print('=' * 60)
    print('BUILD TEMPORAL EDGES v2 -- Timestamp-based (100% coverage)')
    print('DB: ' + DB_PATH)
    print('Neighbors: +/-' + str(NEIGHBORS) + ', Weight: ' + str(WEIGHT))
    print('=' * 60)

    conn = get_connection(DB_PATH)
    cursor = conn.cursor()

    # Load all nodes
    cursor.execute('SELECT id, timestamp, t_event_start FROM nodes ORDER BY id ASC')
    all_nodes = cursor.fetchall()
    total = len(all_nodes)

    with_t_event = sum(1 for n in all_nodes if n['t_event_start'])
    print('')
    print('Total nodes: ' + str(total))
    print('With t_event_start: ' + str(with_t_event) + ' (' + str(round(with_t_event/total*100, 1)) + '%)')
    print('Timestamp only: ' + str(total - with_t_event) + ' (' + str(round((total-with_t_event)/total*100, 1)) + '%)')

    # Sort by effective time, tiebreaker = id
    sorted_nodes = sorted(
        all_nodes,
        key=lambda n: (get_effective_time(n) or '', n['id'])
    )

    print('')
    print('Time range:')
    print('  First: ' + get_effective_time(sorted_nodes[0])[:19])
    print('  Last:  ' + get_effective_time(sorted_nodes[-1])[:19])

    # Check existing temporal edges -- keep v1, INSERT OR IGNORE prevents duplicates
    cursor.execute("SELECT COUNT(*) FROM edges WHERE edge_type IN ('TEMPORAL_BEFORE', 'TEMPORAL_AFTER')")
    old_count = cursor.fetchone()[0]
    print('')
    print('Existing temporal edges: ' + str(old_count) + ' (keeping, INSERT OR IGNORE prevents duplicates)')

    # Build new edges
    existing = set()
    # Pre-load existing to avoid duplicates
    cursor.execute("SELECT source_id, target_id FROM edges WHERE edge_type IN ('TEMPORAL_BEFORE', 'TEMPORAL_AFTER')")
    for row in cursor.fetchall():
        existing.add((row['source_id'], row['target_id']))

    created_before = 0
    created_after = 0

    for i, node in enumerate(sorted_nodes):
        nid = node['id']
        left_start = max(0, i - NEIGHBORS)

        for j in range(left_start, i):
            older_id = sorted_nodes[j]['id']

            # older -> current = TEMPORAL_BEFORE
            key_b = (older_id, nid)
            if key_b not in existing:
                cursor.execute(
                    "INSERT OR IGNORE INTO edges (source_id, target_id, weight, edge_type) VALUES (?, ?, ?, ?)",
                    (older_id, nid, WEIGHT, 'TEMPORAL_BEFORE')
                )
                existing.add(key_b)
                created_before += 1

            # current -> older = TEMPORAL_AFTER
            key_a = (nid, older_id)
            if key_a not in existing:
                cursor.execute(
                    "INSERT OR IGNORE INTO edges (source_id, target_id, weight, edge_type) VALUES (?, ?, ?, ?)",
                    (nid, older_id, WEIGHT, 'TEMPORAL_AFTER')
                )
                existing.add(key_a)
                created_after += 1

        if i % 200 == 0 and i > 0:
            conn.commit()
            print('  Progress: ' + str(i) + '/' + str(total) + ' nodes, BEFORE=' + str(created_before) + ', AFTER=' + str(created_after))

    conn.commit()

    total_created = created_before + created_after
    print('')
    print('=' * 60)
    print('DONE')
    print('  TEMPORAL_BEFORE created: ' + str(created_before))
    print('  TEMPORAL_AFTER  created: ' + str(created_after))
    print('  Total new edges:         ' + str(total_created))
    print('  Coverage: ' + str(total) + '/' + str(total) + ' nodes (100%)')

    # Verify
    cursor.execute("SELECT COUNT(*) FROM edges WHERE edge_type='TEMPORAL_BEFORE'")
    verify = cursor.fetchone()[0]
    print('  Verify in DB: ' + str(verify) + ' TEMPORAL_BEFORE edges')

    conn.close()
    print('')
    print('STOP -- show result to Artem')


if __name__ == '__main__':
    main()