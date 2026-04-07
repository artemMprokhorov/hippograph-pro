#!/usr/bin/env python3
"""
HippoGraph Evolution Analyzer (item #45)

Compares multiple snapshot DBs to track graph evolution over time.
Run periodically to discover patterns in growth, structure, and emergence.

Usage:
    python3 evolution_analyzer.py                    # auto-discover snapshots
    python3 evolution_analyzer.py --top              # show top PageRank nodes
    python3 evolution_analyzer.py --categories       # category breakdown
"""
import sqlite3, os, sys, argparse
from datetime import datetime
from pathlib import Path

SNAPSHOT_DIRS = [
    'data',
    'backups',
]

LABELS = {
    'memory_20260127': 'Jan 27 (ANN)',
    'memory_20260210': 'Feb 10 (blend)',
    'hippograph_pro_memory_20260227': 'Feb 27',
    'memory_20260319': 'Mar 19',
    'memory_backup_20260322_supersedes': 'Mar 22 (SUPERSEDES)',
    'memory_backup_20260322_phase2': 'Mar 22 (phase2)',
    'memory.db': 'NOW',
}

# ── Snapshot discovery ───────────────────────────────────────────────────────
def find_snapshots(specific=None):
    if specific:
        return [(Path(p).stat().st_mtime, p) for p in specific if Path(p).exists()]
    found = []
    seen = set()
    for d in SNAPSHOT_DIRS:
        for f in sorted(Path(d).glob('*.db')):
            if f.stat().st_size < 500_000:
                continue
            key = f.stat().st_mtime
            if key in seen:
                continue
            try:
                conn = sqlite3.connect(str(f))
                n = conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0]
                conn.close()
                if n > 50:
                    found.append((key, str(f)))
                    seen.add(key)
            except Exception:
                pass
    found.sort()
    return found

# ── Per-snapshot metrics ─────────────────────────────────────────────────────
def analyze_snapshot(db_path):
    conn = sqlite3.connect(db_path)
    m = {}
    try:
        m['nodes'] = conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0]
        m['edges'] = conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
        try:
            m['entities'] = conn.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
        except Exception:
            m['entities'] = 0

        # Category distribution
        cats = conn.execute(
            'SELECT category, COUNT(*) c FROM nodes GROUP BY category ORDER BY c DESC LIMIT 8'
        ).fetchall()
        m['top_categories'] = cats

        # Edge type distribution
        etypes = conn.execute(
            'SELECT edge_type, COUNT(*) c FROM edges GROUP BY edge_type ORDER BY c DESC'
        ).fetchall()
        m['edge_types'] = {t: c for t, c in etypes}

        # Importance distribution
        imps = conn.execute(
            'SELECT importance, COUNT(*) FROM nodes GROUP BY importance'
        ).fetchall()
        m['importance'] = {i: c for i, c in imps}

        # Top PageRank nodes
        try:
            top_pr = conn.execute(
                'SELECT id, category, pagerank, substr(content,1,50) FROM nodes ORDER BY pagerank DESC LIMIT 5'
            ).fetchall()
            m['top_pagerank'] = top_pr
        except Exception:
            m['top_pagerank'] = []

        # Avg connections per node
        m['avg_degree'] = round(m['edges'] / max(m['nodes'], 1), 1)

        # Emotional notes
        try:
            m['emotional_notes'] = conn.execute(
                'SELECT COUNT(*) FROM nodes WHERE emotional_intensity > 0'
            ).fetchone()[0]
            m['avg_intensity'] = conn.execute(
                'SELECT AVG(emotional_intensity) FROM nodes WHERE emotional_intensity > 0'
            ).fetchone()[0] or 0
        except Exception:
            m['emotional_notes'] = 0
            m['avg_intensity'] = 0

        # Emergence log (if exists)
        try:
            last_em = conn.execute(
                'SELECT composite_score, timestamp FROM emergence_log ORDER BY id DESC LIMIT 1'
            ).fetchone()
            m['emergence'] = round(last_em[0], 4) if last_em else None
        except Exception:
            m['emergence'] = None

        # DB file size
        m['size_mb'] = round(Path(db_path).stat().st_size / 1024 / 1024, 1)

    finally:
        conn.close()
    return m

# ── Pretty label ─────────────────────────────────────────────────────────────
def label(path):
    name = Path(path).stem
    for k, v in LABELS.items():
        if k in name:
            return v
    # fallback: extract date from name
    for part in name.split('_'):
        if len(part) == 8 and part.isdigit():
            return part[:4] + '-' + part[4:6] + '-' + part[6:]
    return name[-20:]

# ── Main report ──────────────────────────────────────────────────────────────
def print_evolution(snapshots):
    print('=' * 70)
    print('HIPPOGRAPH EVOLUTION ANALYSIS')
    print(f'Snapshots analyzed: {len(snapshots)}')
    print('=' * 70)

    prev = None
    rows = []
    for mtime, path in snapshots:
        lbl = label(path)
        m = analyze_snapshot(path)
        rows.append((lbl, m, path))

    # Growth table
    print(f'\n{"Snapshot":<25} {"Nodes":>6} {"Edges":>8} {"Deg":>6} {"Size":>6} {"Emerge":>8}')
    print('-' * 65)
    prev_nodes = 0
    for lbl, m, path in rows:
        delta = f'+{m["nodes"]-prev_nodes}' if prev_nodes else ''
        em = f'{m["emergence"]:.3f}' if m["emergence"] else '  n/a '
        print(f'{lbl:<25} {m["nodes"]:>5}{delta:>3} {m["edges"]:>8,} {m["avg_degree"]:>6} {m["size_mb"]:>5}MB {em:>8}')
        prev_nodes = m['nodes']

    # Edge type evolution
    print('\n--- Edge type evolution ---')
    KEY_TYPES = ['entity', 'semantic', 'consolidation', 'EMOTIONAL_RESONANCE',
                 'GENERALIZES', 'INSTANTIATES', 'SUPERSEDES', 'TEMPORAL_BEFORE']
    header = f'{"Type":<22}' + ''.join(f'{label(p):>10}' for _, _, p in rows)
    print(header)
    for et in KEY_TYPES:
        row = f'{et:<22}'
        for _, m, _ in rows:
            cnt = m['edge_types'].get(et, 0)
            row += f'{cnt:>10,}' if cnt else f'{"":>10}'
        print(row)

    # Category growth (latest only, top 10)
    print('\n--- Categories (current) ---')
    lbl, m, _ = rows[-1]
    for cat, cnt in m['top_categories']:
        bar = '█' * min(cnt // 5, 30)
        print(f'  {cat:<25} {cnt:>4}  {bar}')

    # Emotional evolution
    print('\n--- Emotional richness ---')
    for lbl, m, _ in rows:
        pct = round(m['emotional_notes'] / max(m['nodes'], 1) * 100)
        avg = round(m['avg_intensity'], 1)
        print(f'  {lbl:<25} {m["emotional_notes"]:>4} notes ({pct}%)  avg intensity {avg}')

    # Top PageRank (latest)
    print('\n--- Top PageRank nodes (current) ---')
    lbl, m, _ = rows[-1]
    for nid, cat, pr, content in m['top_pagerank']:
        print(f'  #{nid} [{cat}] PR={pr:.3f}: {content}...')

    print('\n' + '=' * 70)
    print(f'Run again periodically to track evolution.')
    print('=' * 70)

# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HippoGraph Evolution Analyzer')
    parser.add_argument('--db', nargs='+', help='Specific DB files to compare')
    parser.add_argument('--latest', type=int, default=0, help='Only last N snapshots')
    args = parser.parse_args()

    snapshots = find_snapshots(args.db)
    if args.latest:
        snapshots = snapshots[-args.latest:]

    if not snapshots:
        print('No snapshots found.')
        sys.exit(1)

    print_evolution(snapshots)