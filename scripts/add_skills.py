#!/usr/bin/env python3
"""
Batch add skills to Neural Memory directly via SQLite
Bypasses MCP and context window limits

Usage: python3 add_skills.py skills.json
"""

import sqlite3
import json
import sys
from datetime import datetime

DEFAULT_DB = "./data/memory.db"

def format_skill_content(skill):
    """Format skill data as memory content"""
    content = f"SKILL LEARNED: {skill['name']}"
    
    if 'purpose' in skill:
        content += f"\n\nPurpose: {skill['purpose']}"
    
    if 'when_to_use' in skill:
        content += f"\n\nWhen to use: {skill['when_to_use']}"
    
    if 'tags' in skill:
        tags_str = ", ".join(skill['tags'])
        content += f"\n\nTags: {tags_str}"
    
    return content

def add_skills_to_db(skills_file, db_path):
    """Add skills directly to SQLite database"""
    
    with open(skills_file, 'r') as f:
        skills = json.load(f)
    
    print(f"📚 Loaded {len(skills)} skills")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    added = 0
    skipped = 0
    
    for skill in skills:
        content = format_skill_content(skill)
        category = skill.get('category', 'general')
        importance = skill.get('importance', 'normal')
        intensity = skill.get('intensity', 5)
        
        # Check for duplicates
        cursor.execute(
            "SELECT id FROM nodes WHERE content LIKE ? LIMIT 1",
            (f"%{skill['name']}%",)
        )
        
        if cursor.fetchone():
            print(f"⏭️  Skipped: {skill['name']} (duplicate)")
            skipped += 1
            continue
        
        # Insert
        cursor.execute("""
            INSERT INTO nodes (
                content, category, timestamp, importance,
                emotional_intensity, emotional_tone, emotional_reflection
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            content, category, datetime.now().isoformat(), importance,
            intensity, 'learning, growth', f'Added skill {skill["name"]}'
        ))
        
        added += 1
        print(f"✅ Added: {skill['name']} (category: {category})")
    
    conn.commit()
    conn.close()
    
    print(f"\n📊 Added: {added}, Skipped: {skipped}")
    return added, skipped

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 add_skills.py skills.json [--db /path/to/db]")
        sys.exit(1)
    
    skills_file = sys.argv[1]
    db_path = DEFAULT_DB
    
    if '--db' in sys.argv:
        db_idx = sys.argv.index('--db')
        if db_idx + 1 < len(sys.argv):
            db_path = sys.argv[db_idx + 1]
    
    print(f"🎯 Database: {db_path}\n")
    add_skills_to_db(skills_file, db_path)
    print("\n✅ Done!")
