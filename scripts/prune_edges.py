#!/usr/bin/env python3
"""
Edge Pruning - OPTIONAL Enterprise Feature

⚠️  NOT RECOMMENDED for personal use
   Weak connections may become important as your memory grows
"""
import sqlite3, sys

def analyze(db):
    conn = sqlite3.connect(db)
    total = conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
    sem = conn.execute('SELECT COUNT(*) FROM edges WHERE edge_type="semantic"').fetchone()[0]
    ent = total - sem
    
    weights = sorted([r[0] for r in conn.execute('SELECT weight FROM edges WHERE edge_type="semantic"')])
    
    print(f'Total: {total:,} edges')
    print(f'  Semantic: {sem:,}\n  Entity: {ent:,}')
    if weights:
        print(f'\nSemantic weights: min={min(weights):.3f} median={weights[len(weights)//2]:.3f} max={max(weights):.3f}')
        print('\nBelow threshold:')
        for t in [0.50, 0.55, 0.60, 0.65]:
            c = sum(1 for w in weights if w < t)
            print(f'  <{t}: {c:,} ({c/len(weights)*100:.1f}%)')
    conn.close()

def prune(db, threshold, confirm):
    conn = sqlite3.connect(db)
    to_remove = conn.execute('SELECT COUNT(*) FROM edges WHERE edge_type="semantic" AND weight < ?', (threshold,)).fetchone()[0]
    
    if not confirm:
        print(f'DRY RUN: Would remove {to_remove} semantic edges < {threshold}')
        print('Add --confirm to actually delete')
        conn.close()
        return
    
    conn.execute('DELETE FROM edges WHERE edge_type="semantic" AND weight < ?', (threshold,))
    conn.commit()
    print(f'✅ Removed {to_remove} edges')
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage:\n  --analyze: python3 prune_edges.py <db> --analyze\n  --prune: python3 prune_edges.py <db> --threshold 0.6 [--confirm]')
        sys.exit(1)
    
    db = sys.argv[1]
    if '--analyze' in sys.argv:
        analyze(db)
    else:
        t = 0.6
        for i, a in enumerate(sys.argv):
            if a == '--threshold': t = float(sys.argv[i+1])
        prune(db, t, '--confirm' in sys.argv)
