#!/usr/bin/env python3
"""
Re-extract entities for all notes using multilingual NER.
Replaces old entity links (from en_core_web_sm) with new ones
from xx_ent_wiki_sm for Russian text and en_core_web_sm for English.
Preserves semantic edges — only entity edges are rebuilt.
"""
import sqlite3
import sys
import os

sys.path.insert(0, '/app/src')
from entity_extractor import extract_entities, detect_language

DB_PATH = os.getenv('DB_PATH', '/app/data/memory.db')

def get_or_create_entity(cursor, name, entity_type):
    """Get existing entity ID or create new one.
    Note: entities table has UNIQUE on name only (not name+type).
    """
    cursor.execute(
        "SELECT id FROM entities WHERE name = ?",
        (name,)
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO entities (name, entity_type) VALUES (?, ?)",
        (name, entity_type)
    )
    return cursor.lastrowid


def find_shared_entity_nodes(cursor, entity_id, exclude_node_id):
    """Find all other nodes that share this entity."""
    cursor.execute(
        "SELECT node_id FROM node_entities WHERE entity_id = ? AND node_id != ?",
        (entity_id, exclude_node_id)
    )
    return [row[0] for row in cursor.fetchall()]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()

    # Get all notes
    cursor.execute("SELECT id, content FROM nodes ORDER BY id")
    notes = cursor.fetchall()
    total = len(notes)
    print(f"Processing {total} notes...")

    # Stats
    stats = {
        'processed': 0,
        'old_entity_edges_removed': 0,
        'old_node_entities_removed': 0,
        'new_entities_created': 0,
        'new_node_entities_created': 0,
        'new_entity_edges_created': 0,
        'ru_notes': 0,
        'en_notes': 0,
        'errors': 0,
    }

    for i, (note_id, content) in enumerate(notes):
        try:
            lang = detect_language(content)
            if lang == 'ru':
                stats['ru_notes'] += 1
            else:
                stats['en_notes'] += 1

            # Step 1: Remove old entity edges for this note
            cursor.execute(
                "DELETE FROM edges WHERE edge_type = 'entity' AND (source_id = ? OR target_id = ?)",
                (note_id, note_id)
            )
            stats['old_entity_edges_removed'] += cursor.rowcount

            # Step 2: Remove old node_entities for this note
            cursor.execute(
                "DELETE FROM node_entities WHERE node_id = ?",
                (note_id,)
            )
            stats['old_node_entities_removed'] += cursor.rowcount

            # Step 3: Extract entities with new multilingual NER
            entities = extract_entities(content)

            # Step 4: Create node_entities and entity edges
            for entity_text, entity_type in entities:
                entity_id = get_or_create_entity(cursor, entity_text, entity_type)
                # Link node to entity
                cursor.execute(
                    "INSERT OR IGNORE INTO node_entities (node_id, entity_id) VALUES (?, ?)",
                    (note_id, entity_id)
                )
                if cursor.rowcount > 0:
                    stats['new_node_entities_created'] += 1

                # Create entity edges to other nodes sharing this entity
                shared_nodes = find_shared_entity_nodes(cursor, entity_id, note_id)
                for other_node_id in shared_nodes:
                    # Check if edge already exists
                    cursor.execute(
                        "SELECT id FROM edges WHERE source_id = ? AND target_id = ? AND edge_type = 'entity'",
                        (note_id, other_node_id)
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO edges (source_id, target_id, weight, edge_type) VALUES (?, ?, 0.6, 'entity')",
                            (note_id, other_node_id)
                        )
                        stats['new_entity_edges_created'] += 1
                    # Reverse edge
                    cursor.execute(
                        "SELECT id FROM edges WHERE source_id = ? AND target_id = ? AND edge_type = 'entity'",
                        (other_node_id, note_id)
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO edges (source_id, target_id, weight, edge_type) VALUES (?, ?, 0.6, 'entity')",
                            (other_node_id, note_id)
                        )
                        stats['new_entity_edges_created'] += 1

            stats['processed'] += 1

            # Progress every 50 notes
            if (i + 1) % 50 == 0:
                print(f"  [{i+1}/{total}] lang={lang} entities={len(entities)}")
                conn.commit()

        except Exception as e:
            stats['errors'] += 1
            print(f"  ERROR note #{note_id}: {e}")

    conn.commit()

    # Clean up orphaned entities (entities with no node_entities links)
    cursor.execute("""
        DELETE FROM entities WHERE id NOT IN (
            SELECT DISTINCT entity_id FROM node_entities
        )
    """)
    orphaned = cursor.rowcount
    conn.commit()
    conn.close()

    print(f"\n{'='*50}")
    print(f"RE-EXTRACTION COMPLETE")
    print(f"{'='*50}")
    print(f"Notes processed:        {stats['processed']}/{total}")
    print(f"  English notes:        {stats['en_notes']}")
    print(f"  Russian notes:        {stats['ru_notes']}")
    print(f"Old entity edges removed: {stats['old_entity_edges_removed']}")
    print(f"Old node_entities removed: {stats['old_node_entities_removed']}")
    print(f"New node_entities created: {stats['new_node_entities_created']}")
    print(f"New entity edges created:  {stats['new_entity_edges_created']}")
    print(f"Orphaned entities cleaned: {orphaned}")
    print(f"Errors: {stats['errors']}")


if __name__ == "__main__":
    main()
