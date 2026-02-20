#!/usr/bin/env python3
"""
Database layer for Neural Memory Graph
SQLite with graph schema: nodes, edges, entities
"""

import sqlite3
import os
import json
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "/app/data/memory.db")
ENABLE_EMOTIONAL_MEMORY = os.getenv("ENABLE_EMOTIONAL_MEMORY", "false").lower() == "true"


@contextmanager
def get_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize database schema"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Nodes table (notes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                timestamp TEXT,
                embedding BLOB,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0,
                importance TEXT DEFAULT 'normal',
                emotional_tone TEXT,
                emotional_intensity INTEGER DEFAULT 5,
                emotional_reflection TEXT,
                t_event_start TEXT,
                t_event_end TEXT,
                temporal_expressions TEXT
            )
        """)
        
        # Migration: add importance column if missing (for existing databases)
        cursor.execute("PRAGMA table_info(nodes)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'importance' not in columns:
            cursor.execute("ALTER TABLE nodes ADD COLUMN importance TEXT DEFAULT 'normal'")
            print("  ↳ Added 'importance' column to nodes table")
        
        # Migration: add bi-temporal columns if missing
        if 't_event_start' not in columns:
            cursor.execute("ALTER TABLE nodes ADD COLUMN t_event_start TEXT")
            cursor.execute("ALTER TABLE nodes ADD COLUMN t_event_end TEXT")
            cursor.execute("ALTER TABLE nodes ADD COLUMN temporal_expressions TEXT")
            print("  ↳ Added bi-temporal columns to nodes table")
        
        # Edges table (connections between nodes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                weight REAL DEFAULT 0.5,
                edge_type TEXT DEFAULT 'semantic',
                created_at TEXT,
                FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES nodes(id) ON DELETE CASCADE,
                UNIQUE(source_id, target_id, edge_type)
            )
        """)
        
        # Entities table (extracted concepts, people, projects)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                entity_type TEXT DEFAULT 'concept'
            )
        """)
        
        # Node-Entity linking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_entities (
                node_id INTEGER NOT NULL,
                entity_id INTEGER NOT NULL,
                PRIMARY KEY (node_id, entity_id),
                FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
            )
        """)
        
        # Indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_node_entities_node ON node_entities(node_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_node_entities_entity ON node_entities(entity_id)")
        
    print(f"✅ Database initialized: {DB_PATH}")


def create_node(content, category="general", embedding=None, importance="normal", 
                emotional_tone=None, emotional_intensity=5, emotional_reflection=None,
                t_event_start=None, t_event_end=None, temporal_expressions=None):
    """Create a new node (note). 
    Importance: 'critical', 'normal', or 'low'
    Emotional fields: tone (keywords), intensity (0-10), reflection (narrative) - only if ENABLE_EMOTIONAL_MEMORY=true
    Bi-temporal: t_event_start/end (nullable) = when event happened, temporal_expressions = JSON array of extracted expressions
    """
    timestamp = datetime.now().isoformat()
    
    # Apply emotional fields only if feature is enabled
    if not ENABLE_EMOTIONAL_MEMORY:
        emotional_tone = None
        emotional_intensity = 5
        emotional_reflection = None
    
    # Auto-extract temporal expressions if not provided
    if t_event_start is None and temporal_expressions is None:
        try:
            from temporal_extractor import extract_temporal_expressions
            ref_date = datetime.fromisoformat(timestamp)
            temporal = extract_temporal_expressions(content, ref_date)
            if temporal["expressions"]:
                temporal_expressions = json.dumps(temporal["expressions"])
                t_event_start = temporal["t_event_start"]
                t_event_end = temporal["t_event_end"]
        except Exception:
            pass  # Graceful degradation — temporal is optional
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO nodes (content, category, timestamp, embedding, last_accessed, access_count, 
               importance, emotional_tone, emotional_intensity, emotional_reflection,
               t_event_start, t_event_end, temporal_expressions) 
               VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)""",
            (content, category, timestamp, embedding, timestamp, importance, 
             emotional_tone, emotional_intensity, emotional_reflection,
             t_event_start, t_event_end, temporal_expressions)
        )
        return cursor.lastrowid


def get_node(node_id):
    """Get node by ID"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_node(node_id, content=None, category=None, embedding=None, importance=None,
                emotional_tone=None, emotional_intensity=None, emotional_reflection=None):
    """Update existing node. Emotional fields only if ENABLE_EMOTIONAL_MEMORY=true"""
    
    # Ignore emotional fields if feature is disabled
    if not ENABLE_EMOTIONAL_MEMORY:
        emotional_tone = None
        emotional_intensity = None
        emotional_reflection = None
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if embedding is not None:
            updates.append("embedding = ?")
            params.append(embedding)
        if importance is not None:
            updates.append("importance = ?")
            params.append(importance)
        if emotional_tone is not None:
            updates.append("emotional_tone = ?")
            params.append(emotional_tone)
        if emotional_intensity is not None:
            updates.append("emotional_intensity = ?")
            params.append(emotional_intensity)
        if emotional_reflection is not None:
            updates.append("emotional_reflection = ?")
            params.append(emotional_reflection)
        
        if not updates:
            return False
        
        # Save current state as version before updating (if content changes)
        if content is not None:
            current = get_node(node_id)
            if current:
                save_note_version(
                    node_id,
                    current['content'],
                    current['category'],
                    current['importance'],
                    current.get('emotional_tone'),
                    current.get('emotional_intensity'),
                    current.get('emotional_reflection')
                )
        
        updates.append("timestamp = ?")
        params.append(datetime.now().isoformat())
        params.append(node_id)
        
        sql = "UPDATE nodes SET " + ", ".join(updates) + " WHERE id = ?"
        cursor.execute(sql, params)
        return cursor.rowcount > 0


def set_importance(node_id, importance):
    """Set importance level for a node: 'critical', 'normal', or 'low'"""
    if importance not in ('critical', 'normal', 'low'):
        raise ValueError("Importance must be 'critical', 'normal', or 'low'")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE nodes SET importance = ? WHERE id = ?", (importance, node_id))
        return cursor.rowcount > 0


def delete_node(node_id):
    """Delete node and return its data"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT content, category FROM nodes WHERE id = ?", (node_id,))
        node = cursor.fetchone()
        if not node:
            return None
        cursor.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        return dict(node)


def get_all_nodes():
    """Get all nodes ordered by timestamp"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM nodes ORDER BY timestamp DESC")
        return [dict(row) for row in cursor.fetchall()]


def touch_node(node_id):
    """Update last_accessed and increment access_count"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE nodes SET last_accessed = ?, access_count = access_count + 1 WHERE id = ?",
            (datetime.now().isoformat(), node_id)
        )


def create_edge(source_id, target_id, weight=0.5, edge_type="semantic"):
    """Create edge between nodes (or update weight if exists)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO edges (source_id, target_id, weight, edge_type, created_at) VALUES (?, ?, ?, ?, ?)",
                (source_id, target_id, weight, edge_type, datetime.now().isoformat())
            )
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Edge exists, update weight if higher
            cursor.execute(
                "UPDATE edges SET weight = MAX(weight, ?) WHERE source_id = ? AND target_id = ? AND edge_type = ?",
                (weight, source_id, target_id, edge_type)
            )
            return None


def get_connected_nodes(node_id):
    """Get all nodes connected to given node"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT DISTINCT n.*, e.weight, e.edge_type
               FROM nodes n
               JOIN edges e ON (n.id = e.target_id AND e.source_id = ?)
                            OR (n.id = e.source_id AND e.target_id = ?)
               WHERE n.id != ?""",
            (node_id, node_id, node_id)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_or_create_entity(name, entity_type="concept"):
    """Get existing entity or create new one"""
    name_lower = name.lower().strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM entities WHERE LOWER(name) = ?", (name_lower,))
        row = cursor.fetchone()
        if row:
            return row["id"]
        cursor.execute("INSERT INTO entities (name, entity_type) VALUES (?, ?)", (name, entity_type))
        return cursor.lastrowid


def link_node_to_entity(node_id, entity_id):
    """Link node to entity"""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO node_entities (node_id, entity_id) VALUES (?, ?)", (node_id, entity_id))
            return True
        except sqlite3.IntegrityError:
            return False


def get_nodes_by_entity(entity_id):
    """Get all nodes linked to an entity"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT n.* FROM nodes n JOIN node_entities ne ON n.id = ne.node_id WHERE ne.entity_id = ?",
            (entity_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_entity_counts_batch():
    """Get entity count per node as dict {node_id: count}"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT node_id, COUNT(*) FROM node_entities GROUP BY node_id")
        return {row[0]: row[1] for row in cursor.fetchall()}


def get_stats():
    """Get database statistics"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM nodes")
        total_nodes = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM edges")
        total_edges = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM entities")
        total_entities = cursor.fetchone()["count"]
        
        cursor.execute("SELECT category, COUNT(*) as count FROM nodes GROUP BY category")
        by_category = {row["category"]: row["count"] for row in cursor.fetchall()}
        
        cursor.execute("SELECT edge_type, COUNT(*) as count FROM edges GROUP BY edge_type")
        by_edge_type = {row["edge_type"]: row["count"] for row in cursor.fetchall()}
        
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "total_entities": total_entities,
            "nodes_by_category": by_category,
            "edges_by_type": by_edge_type
        }


def get_all_edges():
    """Get all edges from database for graph cache"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT source_id, target_id, weight, edge_type
               FROM edges"""
        )
        return [dict(row) for row in cursor.fetchall()]


def save_note_version(note_id, content, category, importance, 
                      emotional_tone=None, emotional_intensity=None, emotional_reflection=None):
    """
    Save current note state as a version before updating
    Keeps last 5 versions by default
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get current max version number for this note
        cursor.execute(
            "SELECT COALESCE(MAX(version_number), 0) FROM note_versions WHERE note_id = ?",
            (note_id,)
        )
        max_version = cursor.fetchone()[0]
        new_version = max_version + 1
        
        # Insert new version
        cursor.execute("""
            INSERT INTO note_versions 
            (note_id, version_number, content, category, importance, 
             emotional_tone, emotional_intensity, emotional_reflection, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (note_id, new_version, content, category, importance,
              emotional_tone, emotional_intensity, emotional_reflection,
              datetime.now().isoformat()))
        
        # Keep only last 5 versions - delete older ones
        cursor.execute("""
            DELETE FROM note_versions 
            WHERE note_id = ? AND version_number <= ?
        """, (note_id, new_version - 5))
        
        return new_version


def get_note_history(note_id, limit=5):
    """Get version history for a note"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT version_number, content, category, importance,
                   emotional_tone, emotional_intensity, emotional_reflection, created_at
            FROM note_versions
            WHERE note_id = ?
            ORDER BY version_number DESC
            LIMIT ?
        """, (note_id, limit))
        
        versions = []
        for row in cursor.fetchall():
            versions.append(dict(row))
        return versions


def get_version_count(note_id):
    """Get total number of versions for a note"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM note_versions WHERE note_id = ?",
            (note_id,)
        )
        return cursor.fetchone()[0]


def restore_note_version(note_id, version_number):
    """Restore a note to a previous version"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get the version data
        cursor.execute("""
            SELECT content, category, importance, emotional_tone, 
                   emotional_intensity, emotional_reflection
            FROM note_versions
            WHERE note_id = ? AND version_number = ?
        """, (note_id, version_number))
        
        version = cursor.fetchone()
        if not version:
            return None
        
        version_dict = dict(version)
        
        # Save current state as a version before restoring
        cursor.execute("SELECT * FROM nodes WHERE id = ?", (note_id,))
        current = cursor.fetchone()
        if current:
            current_dict = dict(current)
            save_note_version(
                note_id,
                current_dict['content'],
                current_dict['category'],
                current_dict['importance'],
                current_dict.get('emotional_tone'),
                current_dict.get('emotional_intensity'),
                current_dict.get('emotional_reflection')
            )
        
        # Restore the version
        cursor.execute("""
            UPDATE nodes
            SET content = ?, category = ?, importance = ?,
                emotional_tone = ?, emotional_intensity = ?, emotional_reflection = ?,
                timestamp = ?
            WHERE id = ?
        """, (version_dict['content'], version_dict['category'], version_dict['importance'],
              version_dict['emotional_tone'], version_dict['emotional_intensity'],
              version_dict['emotional_reflection'], datetime.now().isoformat(), note_id))
        
        return cursor.rowcount > 0
