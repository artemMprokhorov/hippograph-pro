#!/usr/bin/env python3
"""
Enriched Fragments via API (V2 corrected)
Creates fragments through add_note API so they get
proper semantic edges from ANN (not isolated in graph).

Variant 1: parent stays (importance=low via API)
Variant 2: parent deleted after fragments created
"""
import sys, os, json, requests, sqlite3
sys.path.insert(0, '/app/src')
os.environ.setdefault('DB_PATH', '/app/data/memory.db')

API_URL = os.environ.get('API_URL', 'http://localhost:5007')
API_KEY = os.environ.get('NEURAL_API_KEY', 'change_me_in_production')
DB_PATH = os.environ.get('DB_PATH', '/app/data/memory.db')

ELIGIBLE = {'milestone', 'benchmark', 'breakthrough',
             'architecture-decision', 'learned-skill', 'research',
             'project-milestone', 'project-planning'}
SKIP = {'self-reflection', 'emotional-reflection',
        'working-memory', 'abstract-topic', 'atomic-fact', 'enriched-fragment'}


def extract_facts(content):
    import re
    facts = []
    NOISE = {'next', 'step', 'see', 'use', 'run', 'get', 'list',
             'item', 'note', 'done', 'also'}
    patterns = [
        r'([A-Za-z][\w@#_-]{2,}[\s:=]+[0-9]+\.?[0-9]*\s*[%kKmMpp]*)',
        r'([0-9]+\.?[0-9]*\s*[%pp]+\s+[A-Za-z][\w@#_-]{3,})',
        r'(Recall@[0-9]+\s*[=:]?\s*[0-9]+\.?[0-9]*[%]?)',
        r'([A-Z][\w-]{2,}\s*[=:]\s*[0-9]+\.?[0-9]*)',
    ]
    seen = set()
    for pat in patterns:
        for m in re.finditer(pat, content):
            fact = m.group(1).strip().rstrip(',.:;')
            words = fact.split()
            if (8 <= len(fact) <= 70 and len(words) >= 2
                    and not any(w.lower() in NOISE for w in words)
                    and fact not in seen):
                seen.add(fact)
                facts.append(fact)
        if len(facts) >= 3:
            break
    return facts[:5]


def run(variant=1, max_notes=200):
    conn = sqlite3.connect(DB_PATH)
    headers = {'Content-Type': 'application/json', 'X-API-Key': API_KEY}

    # Already processed parents
    processed = set(
        r[0] for r in conn.execute(
            "SELECT DISTINCT source_id FROM edges WHERE edge_type='PART_OF'"
        ).fetchall()
    )

    rows = conn.execute(
        'SELECT id, content, category, emotional_tone, emotional_reflection '
        'FROM nodes WHERE category NOT IN ({}) ORDER BY id DESC LIMIT {}'.format(
            ','.join('"' + s + '"' for s in SKIP), max_notes
        )
    ).fetchall()

    eligible = [r for r in rows if r[2] in ELIGIBLE and r[0] not in processed]
    print(f'Processing {len(eligible)} memories via API (variant={variant})...')

    fragments_created = 0
    parents_affected = 0

    for parent_id, content, category, etone, ereflect in eligible:
        facts = extract_facts(content)
        if not facts:
            continue

        emotion = (etone or 'neutral').split(',')[0].strip()
        narrative = (ereflect or '').strip()[:100]

        for fact in facts:
            frag_content = (
                f'FRAGMENT: {fact}\n'
                f'CONTEXT: {category} memory\n'
                f'EMOTION: {emotion}\n'
                f'NARRATIVE: {narrative}\n'
                f'SOURCE: #{parent_id}'
            )
            # Use add_note API -> gets proper ANN semantic links automatically
            payload = {
                'content': frag_content,
                'category': 'enriched-fragment',
                'importance': 'normal',
                'emotional_tone': emotion,
                'emotional_intensity': 3,
                'force': False,
                'skip_ner': True,  # fragments don't need entity extraction
            }
            try:
                resp = requests.post(
                    f'{API_URL}/api/add_note?api_key={API_KEY}',
                    headers={'Content-Type': 'application/json'},
                    json=payload, timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    frag_id = data.get('id')
                    if frag_id:
                        # Add PART_OF edge manually
                        conn.execute(
                            'INSERT OR IGNORE INTO edges '
                            '(source_id, target_id, edge_type, weight, created_at)'
                            ' VALUES (?, ?, ?, ?, datetime("now"))',
                            (frag_id, parent_id, 'PART_OF', 0.85)
                        )
                        conn.execute(
                            'INSERT OR IGNORE INTO edges '
                            '(source_id, target_id, edge_type, weight, created_at)'
                            ' VALUES (?, ?, ?, ?, datetime("now"))',
                            (parent_id, frag_id, 'PART_OF', 0.85)
                        )
                        fragments_created += 1
            except Exception as e:
                print(f'  API error: {e}')

        # Variant 1: demote parent
        if variant == 1:
            conn.execute(
                "UPDATE nodes SET importance='low' WHERE id=?", (parent_id,)
            )
        # Variant 2: delete parent
        elif variant == 2:
            conn.execute('DELETE FROM edges WHERE source_id=? OR target_id=?',
                         (parent_id, parent_id))
            conn.execute('DELETE FROM nodes WHERE id=?', (parent_id,))
        parents_affected += 1

    conn.commit()
    conn.close()
    print(f'Done: {fragments_created} fragments created, {parents_affected} parents affected')
    return fragments_created


if __name__ == '__main__':
    import sys
    variant = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run(variant=variant)