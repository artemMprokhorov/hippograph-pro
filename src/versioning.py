#!/usr/bin/env python3
"""
Note versioning functions for database.py
Handles version history for notes
"""

from datetime import datetime
from database import get_connection


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
