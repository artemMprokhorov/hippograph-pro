import sys, re, json
import numpy as np
sys.path.insert(0, '/app/src')
from contradiction_detection import has_contradiction_signal, cosine_similarity
import sqlite3

conn = sqlite3.connect('/app/data/memory.db')
rows = conn.execute('SELECT id, content, embedding, timestamp FROM nodes WHERE id IN (813, 815)').fetchall()
conn.close()

print('=== INTROSPECTION EXPERIMENT ===')
for r in rows:
    found, signals = has_contradiction_signal(r[1])
    print(f'\n#{r[0]}: {r[1][:100]}...')
    print(f'  has_signal: {found}, signals: {signals}')

# Compute similarity
try:
    emb1 = np.frombuffer(rows[0][2], dtype=np.float32)
    emb2 = np.frombuffer(rows[1][2], dtype=np.float32)
    sim = cosine_similarity(emb1, emb2)
    print(f'\nSimilarity #813 <-> #815: {sim:.3f}')
except Exception as e:
    print(f'Embedding error: {e}')
    # Try JSON
    try:
        emb1 = np.array(json.loads(rows[0][2]))
        emb2 = np.array(json.loads(rows[1][2]))
        sim = cosine_similarity(emb1, emb2)
        print(f'Similarity (json) #813 <-> #815: {sim:.3f}')
    except Exception as e2:
        print(f'JSON error too: {e2}')
        print(f'Embedding type: {type(rows[0][2])}, preview: {str(rows[0][2])[:50]}')

# Manual signal check with RU patterns
PATTERNS = [
    r'\bникогда\b', r'\bвсегда\b', r'\bне проверила\b', r'\bпротиворечит\b',
    r'\bnever\b', r'\balways\b', r'\bmistake\b', r'\bcontradicts\b',
    r'\bне верифицировала\b', r'\bошибка\b'
]
print('\n=== Manual pattern check ===')
for r in rows:
    found = [p for p in PATTERNS if re.search(p, r[1], re.IGNORECASE)]
    print(f'#{r[0]}: {found}')