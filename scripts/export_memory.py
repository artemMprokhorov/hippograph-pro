#!/usr/bin/env python3
"""
Export Neural Memory Graph to JSON
Standalone backup script - run directly on server or with database path
"""

import json
import sqlite3
import sys
import os
from datetime import datetime


def export_database(db_path, output_path=None):
    """Export complete database to JSON"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"memory_export_{timestamp}.json"
    
    print(f"📦 Exporting from: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Export nodes (without embeddings)
    print("   Loading nodes...")
    nodes = []
    for row in conn.execute("""
        SELECT id, content, category, timestamp, importance,
               emotional_tone, emotional_intensity, emotional_reflection,
               last_accessed, access_count
        FROM nodes ORDER BY id
    """):
        nodes.append(dict(row))
    
    # Export edges
    print("   Loading edges...")
    edges = []
    for row in conn.execute("SELECT * FROM edges ORDER BY source_id, target_id"):
        edges.append(dict(row))
    
    # Export entities
    print("   Loading entities...")
    entities = []
    for row in conn.execute("SELECT * FROM entities ORDER BY id"):
        entities.append(dict(row))
    
    # Export node_entities
    print("   Loading relationships...")
    node_entities = []
    for row in conn.execute("SELECT * FROM node_entities"):
        node_entities.append(dict(row))
    
    conn.close()
    
    # Create export object
    export_data = {
        "metadata": {
            "export_date": datetime.now().isoformat(),
            "version": "2.0",
            "source_db": db_path,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "entity_count": len(entities)
        },
        "nodes": nodes,
        "edges": edges,
        "entities": entities,
        "node_entities": node_entities
    }
    
    # Write JSON
    print(f"   Writing to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    file_size = os.path.getsize(output_path)
    
    print(f"\n✅ Export complete!")
    print(f"   Nodes: {len(nodes):,}")
    print(f"   Edges: {len(edges):,}")
    print(f"   Entities: {len(entities):,}")
    print(f"   File: {output_path}")
    print(f"   Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 export_memory.py <database_path> [output.json]")
        print("\nExample:")
        print("  python3 export_memory.py data/memory.db")
        print("  python3 export_memory.py data/memory.db backups/export_$(date +%Y%m%d).json")
        sys.exit(1)
    
    db_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = export_database(db_path, output_path)
    sys.exit(0 if success else 1)
