"""
Tests for Prospective Memory (April 2026) — hippograph-pro (nodes schema).
- step_prospective_memory: pending -> critical, done/cancelled -> low
- dry_run no changes
- overdue detection
"""
import sys
import os
import sqlite3
import tempfile
import pytest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def make_db(tmp_dir):
    db = os.path.join(tmp_dir, 'test.db')
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            category TEXT DEFAULT 'general',
            importance TEXT DEFAULT 'normal',
            tags TEXT,
            embedding BLOB,
            timestamp TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER, target_id INTEGER,
            edge_type TEXT, weight REAL, created_at TEXT
        )
    """)
    conn.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()
    return db


def insert_prospective(db, content, tags, importance='normal'):
    conn = sqlite3.connect(db)
    cur = conn.execute(
        "INSERT INTO nodes (content, category, importance, tags, timestamp) VALUES (?, 'prospective', ?, ?, ?)",
        (content, importance, tags, datetime.now().isoformat())
    )
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid


class TestProspectiveMemoryHippo:

    def test_pending_becomes_critical(self, tmp_path):
        from sleep_compute import step_prospective_memory
        db = make_db(str(tmp_path))
        insert_prospective(db, '[INTENTION] Test task', 'pending')
        result = step_prospective_memory(db, dry_run=False)
        assert result['pending'] == 1
        conn = sqlite3.connect(db)
        imp = conn.execute("SELECT importance FROM nodes WHERE category='prospective'").fetchone()[0]
        conn.close()
        assert imp == 'critical'

    def test_done_becomes_low(self, tmp_path):
        from sleep_compute import step_prospective_memory
        db = make_db(str(tmp_path))
        insert_prospective(db, '[INTENTION] Done task', 'done', 'critical')
        result = step_prospective_memory(db, dry_run=False)
        assert result['done'] == 1
        conn = sqlite3.connect(db)
        imp = conn.execute("SELECT importance FROM nodes WHERE category='prospective'").fetchone()[0]
        conn.close()
        assert imp == 'low'

    def test_cancelled_becomes_low(self, tmp_path):
        from sleep_compute import step_prospective_memory
        db = make_db(str(tmp_path))
        insert_prospective(db, '[INTENTION] Cancelled', 'cancelled', 'critical')
        result = step_prospective_memory(db, dry_run=False)
        assert result['cancelled'] == 1
        conn = sqlite3.connect(db)
        imp = conn.execute("SELECT importance FROM nodes WHERE category='prospective'").fetchone()[0]
        conn.close()
        assert imp == 'low'

    def test_dry_run_no_changes(self, tmp_path):
        from sleep_compute import step_prospective_memory
        db = make_db(str(tmp_path))
        insert_prospective(db, '[INTENTION] Test', 'pending')
        step_prospective_memory(db, dry_run=True)
        conn = sqlite3.connect(db)
        imp = conn.execute("SELECT importance FROM nodes WHERE category='prospective'").fetchone()[0]
        conn.close()
        assert imp == 'normal'

    def test_empty_db(self, tmp_path):
        from sleep_compute import step_prospective_memory
        db = make_db(str(tmp_path))
        result = step_prospective_memory(db, dry_run=False)
        assert result == {'total': 0}

    def test_overdue_marked(self, tmp_path):
        from sleep_compute import step_prospective_memory
        db = make_db(str(tmp_path))
        insert_prospective(db, '[INTENTION] Old task', 'pending due:2020-01-01')
        result = step_prospective_memory(db, dry_run=False)
        assert result['overdue'] == 1
        conn = sqlite3.connect(db)
        content = conn.execute("SELECT content FROM nodes WHERE category='prospective'").fetchone()[0]
        conn.close()
        assert '[OVERDUE]' in content

    def test_mixed_statuses(self, tmp_path):
        from sleep_compute import step_prospective_memory
        db = make_db(str(tmp_path))
        insert_prospective(db, '[INTENTION] Task 1', 'pending')
        insert_prospective(db, '[INTENTION] Task 2', 'pending')
        insert_prospective(db, '[INTENTION] Done 1', 'done', 'critical')
        insert_prospective(db, '[INTENTION] Cancelled 1', 'cancelled', 'critical')
        result = step_prospective_memory(db, dry_run=False)
        assert result['pending'] == 2
        assert result['done'] == 1
        assert result['cancelled'] == 1