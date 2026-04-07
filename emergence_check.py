#!/usr/bin/env python3
"""
Emergence Check -- reads official data from emergence_log table.
Does NOT calculate independently -- just reports what step_emergence_check() logged.

Usage:
    python3 emergence_check.py
    python3 emergence_check.py --last 20
    python3 emergence_check.py --trend
"""
import sqlite3, argparse, sys

DB = 'data/memory.db'


def get_data(limit=10):
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        'SELECT id, timestamp, phi_proxy, self_ref_precision, convergence_score, composite_score '
        'FROM emergence_log ORDER BY id DESC LIMIT ?', (limit,)
    ).fetchall()
    total = conn.execute('SELECT COUNT(*) FROM emergence_log').fetchone()[0]
    first = conn.execute('SELECT composite_score, timestamp FROM emergence_log ORDER BY id ASC LIMIT 1').fetchone()
    conn.close()
    return rows, total, first


def show_latest(rows, total, first):
    latest = rows[0]
    print(f'=== Emergence Log ===')
    print(f'Total measurements: {total}')
    print(f'First ever:  {first[0]:.4f}  ({first[1][:10]})')
    print(f'Latest:      {latest[5]:.4f}  ({latest[1][:19]})')
    delta = latest[5] - first[0]
    pct = delta / first[0] * 100 if first[0] else 0
    print(f'Delta:       {delta:+.4f} ({pct:+.1f}%)')
    print()
    print(f'Latest signals:')
    print(f'  phi_proxy:    {latest[2]:.4f}')
    print(f'  self_ref P@5: {latest[3]:.4f}')
    print(f'  convergence:  {latest[4]:.4f}  <- bottleneck')
    print(f'  composite:    {latest[5]:.4f}')


def show_trend(rows):
    print(f'=== Trend (last {len(rows)} measurements) ===')
    print(f'  {"#":>3}  {"timestamp":<19}  {"phi":>6}  {"self_ref":>8}  {"conv":>8}  {"composite":>9}')
    print(f'  {"-"*3}  {"-"*19}  {"-"*6}  {"-"*8}  {"-"*8}  {"-"*9}')
    for r in reversed(rows):
        print(f'  {r[0]:>3}  {r[1][:19]}  {r[2]:>6.3f}  {r[3]:>8.3f}  {r[4]:>8.4f}  {r[5]:>9.4f}')
    print()
    composites = [r[5] for r in rows]
    print(f'  Range: {min(composites):.4f} - {max(composites):.4f}')
    print(f'  Mean:  {sum(composites)/len(composites):.4f}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--last', type=int, default=10)
    parser.add_argument('--trend', action='store_true')
    args = parser.parse_args()

    rows, total, first = get_data(limit=max(args.last, 10))
    show_latest(rows, total, first)
    print()
    show_trend(rows[:args.last])