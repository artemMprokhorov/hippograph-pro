#!/usr/bin/env python3
"""Retrofit tags for existing notes without them.

Extractive approach (zero LLM cost):
- Category as tag
- Entity names as tags
- Top TF-IDF keywords from content (top 3)
- Importance if critical

Run inside Docker:
  docker exec hippograph python3 /app/scripts/retrofit_tags.py
  docker exec hippograph python3 /app/scripts/retrofit_tags.py --dry-run
"""
import sys
import os
import re
import math
from collections import Counter

sys.path.insert(0, '/app/src')
os.chdir('/app')

from database import get_connection


def tokenize(text):
    """Simple tokenizer matching bm25_index.py"""
    return re.findall(r'[a-zA-Z\u0430-\u044f\u0410-\u042f\u0451\u0401\d_]+', text.lower())


STOPWORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'shall', 'to', 'of', 'in', 'for',
    'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
    'before', 'after', 'above', 'below', 'between', 'out', 'off', 'over',
    'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
    'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more',
    'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
    'same', 'so', 'than', 'too', 'very', 'just', 'because', 'but', 'and',
    'or', 'if', 'while', 'about', 'up', 'down', 'that', 'this', 'these',
    'those', 'it', 'its', 'he', 'she', 'they', 'them', 'we', 'you', 'i',
    'me', 'my', 'your', 'his', 'her', 'our', 'their', 'what', 'which',
    'who', 'whom', 'also', 'still', 'already', 'yet', 'now', 'new',
    # Russian stopwords
    '\u0438', '\u0432', '\u043d\u0430', '\u0441', '\u043f\u043e', '\u0434\u043b\u044f', '\u043a\u0430\u043a', '\u044d\u0442\u043e', '\u0447\u0442\u043e', '\u043d\u0435', '\u0438\u0437', '\u043d\u043e', '\u043a', '\u043e\u0442', '\u043f\u0440\u0438', '\u0435\u0441\u0442\u044c',
    '\u0431\u044b\u043b', '\u0431\u044b\u043b\u0430', '\u0431\u044b\u043b\u043e', '\u0431\u044b\u043b\u0438', '\u0431\u044b\u0442\u044c', '\u0443\u0436\u0435', '\u0442\u043e\u043b\u044c\u043a\u043e', '\u0442\u0430\u043a', '\u0431\u043e\u043b\u0435\u0435', '\u0434\u0430', '\u043d\u0435\u0442',
    '\u044d\u0442\u043e\u0442', '\u044d\u0442\u0430', '\u044d\u0442\u0438', '\u0432\u0441\u0435', '\u043e\u043d', '\u043e\u043d\u0430', '\u043e\u043d\u043e', '\u043e\u043d\u0438', '\u043c\u044b', '\u0432\u044b', '\u044f', '\u0438\u043b\u0438',
    '\u0435\u0441\u043b\u0438', '\u043f\u043e\u0442\u043e\u043c\u0443', '\u043a\u043e\u0433\u0434\u0430', '\u0433\u0434\u0435', '\u0435\u0449\u0435', '\u0435\u0449\u0451', '\u0441\u0435\u0439\u0447\u0430\u0441',
    # Common but non-informative
    'note', 'notes', 'added', 'used', 'using', 'use', 'make', 'made',
    'need', 'needs', 'needed', 'work', 'working', 'works', 'worked',
    'get', 'got', 'set', 'one', 'two', 'three', 'first', 'second',
}


def extract_tfidf_keywords(content, all_doc_freqs, n_docs, top_k=3):
    """Extract top TF-IDF keywords from content."""
    tokens = tokenize(content)
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 2]
    tf = Counter(tokens)
    
    scored = []
    for term, freq in tf.items():
        df = all_doc_freqs.get(term, 1)
        idf = math.log((n_docs + 1) / (df + 1))
        scored.append((term, freq * idf))
    
    scored.sort(key=lambda x: -x[1])
    return [t for t, _ in scored[:top_k]]


def build_doc_freqs():
    """Build document frequency table from all notes."""
    doc_freqs = Counter()
    with get_connection() as conn:
        rows = conn.execute('SELECT content FROM nodes').fetchall()
    
    for row in rows:
        tokens = set(tokenize(row['content']))
        for t in tokens:
            doc_freqs[t] += 1
    
    return doc_freqs, len(rows)


def get_entities_for_node(node_id, conn):
    """Get entity names for a node."""
    rows = conn.execute(
        'SELECT e.name FROM entities e '
        'JOIN node_entities ne ON e.id = ne.entity_id '
        'WHERE ne.node_id = ? LIMIT 5',
        (node_id,)
    ).fetchall()
    return [r['name'] for r in rows]


def generate_tags(node, entities, doc_freqs, n_docs):
    """Generate tags for a note."""
    tags = []
    
    # 1. Category (always useful)
    cat = node['category']
    if cat and cat != 'general':
        tags.append(cat)
    
    # 2. Importance
    if node.get('importance') == 'critical':
        tags.append('critical')
    
    # 3. Top entities (max 3)
    for ent in entities[:3]:
        tag = ent.replace(' ', '-').lower()
        if tag not in tags and len(tag) > 2:
            tags.append(tag)
    
    # 4. TF-IDF keywords (fill up to 5-6 total)
    remaining = max(0, 6 - len(tags))
    if remaining > 0:
        keywords = extract_tfidf_keywords(node['content'], doc_freqs, n_docs, top_k=remaining)
        for kw in keywords:
            if kw not in tags and kw not in [t.replace('-', '') for t in tags]:
                tags.append(kw)
    
    return ' '.join(tags[:6])


def main():
    dry_run = '--dry-run' in sys.argv
    
    print(f"{'DRY RUN: ' if dry_run else ''}Retrofitting tags for existing notes...")
    
    # Build TF-IDF document frequencies
    print('Building document frequency table...')
    doc_freqs, n_docs = build_doc_freqs()
    print(f'  {n_docs} documents, {len(doc_freqs)} unique terms')
    
    # Get all notes without tags
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, content, category, importance FROM nodes WHERE tags IS NULL OR tags = ''"
        ).fetchall()
    
    print(f'  {len(rows)} notes need tags')
    
    if not rows:
        print('Nothing to do.')
        return
    
    updated = 0
    samples = []
    
    with get_connection() as conn:
        for row in rows:
            node = dict(row)
            entities = get_entities_for_node(node['id'], conn)
            tags = generate_tags(node, entities, doc_freqs, n_docs)
            
            if not tags:
                continue
            
            if not dry_run:
                conn.execute(
                    'UPDATE nodes SET tags = ? WHERE id = ?',
                    (tags, node['id'])
                )
            
            updated += 1
            if len(samples) < 10:
                samples.append((node['id'], node['category'], tags, node['content'][:60]))
        
        if not dry_run:
            conn.commit()
    
    print(f'\n{"Would update" if dry_run else "Updated"} {updated} notes')
    print('\nSamples:')
    for nid, cat, tags, preview in samples:
        print(f'  #{nid} [{cat}] tags="{tags}"')
        print(f'    {preview}...')


if __name__ == '__main__':
    main()