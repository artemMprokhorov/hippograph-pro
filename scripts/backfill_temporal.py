#!/usr/bin/env python3
"""
Backfill temporal expressions for existing notes.
Runs temporal_extractor on all notes that don't have t_event_start yet.

Usage:
    python3 scripts/backfill_temporal.py [--db-path data/memory.db] [--dry-run]
"""
import sys
import os
import sqlite3
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from temporal_extractor import extract_temporal_expressions


def backfill(db_path: str, dry_run: bool = False):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all notes without temporal data
    cursor.execute("""
        SELECT id, content, timestamp 
        FROM nodes 
        WHERE t_event_start IS NULL
        ORDER BY id
    """)
    notes = cursor.fetchall()
    print(f"📊 Found {len(notes)} notes without temporal data")
    
    updated = 0
    skipped = 0
    
    for note in notes:
        note_id = note['id']
        content = note['content']
        timestamp = note['timestamp']
        
        # Use note's creation time as reference for relative expressions
        try:
            ref_date = datetime.fromisoformat(timestamp) if timestamp else datetime.now()
        except ValueError:
            ref_date = datetime.now()
        
        result = extract_temporal_expressions(content, ref_date)
        
        if result['t_event_start']:
            if dry_run:
                print(f"  [DRY] #{note_id}: {result['expressions']} → {result['t_event_start'][:10]}")
            else:
                cursor.execute("""
                    UPDATE nodes 
                    SET t_event_start = ?, t_event_end = ?, temporal_expressions = ?
                    WHERE id = ?
                """, (
                    result['t_event_start'],
                    result['t_event_end'],
                    json.dumps(result['expressions']),
                    note_id
                ))
            updated += 1
        else:
            skipped += 1
    
    if not dry_run:
        conn.commit()
    conn.close()
    
    print(f"\n✅ Done: {updated} updated, {skipped} skipped (no temporal content)")
    if dry_run:
        print("   (dry run — no changes written)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-path', default='data/memory.db')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    if not os.path.exists(args.db_path):
        print(f"❌ Database not found: {args.db_path}")
        sys.exit(1)
    
    backfill(args.db_path, args.dry_run)
