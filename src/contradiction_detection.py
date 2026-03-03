"""
Contradiction Detection for Memory Notes

Finds pairs of notes that likely contradict each other:
  1. Semantically similar (cosine > threshold) — same topic
  2. Contain contradiction signals — negation, change, update patterns
  3. Temporal ordering — newer note may supersede older one

Does NOT delete anything. Reports conflicts to contradiction_log table.
Human decides what to do with them.

Zero LLM cost. Pure math + regex patterns.
"""
import re
import sqlite3
import numpy as np
from datetime import datetime
from typing import List, Tuple, Dict, Optional


# --- Contradiction signal patterns ---

# Patterns that suggest a statement is being negated or updated
NEGATION_PATTERNS_EN = [
    r'\bno longer\b', r'\bnot anymore\b', r'\bno more\b',
    r'\bchanged\b', r'\bupdated\b', r'\bmodified\b',
    r'\bnow\s+(?:is|are|was|were|use|uses|works)\b',
    r'\bpreviously\b', r'\bformerly\b', r'\bused to\b',
    r'\binstead\b', r'\breplaced\b', r'\bmigrated\b',
    r'\bswitched\b', r'\bmoved\s+(?:to|from)\b',
    r'\bno longer valid\b', r'\bobsolete\b', r'\bdeprecated\b',
    r'\bcorrection\b', r'\bactually\b', r'\bin fact\b',
    r'\bwas wrong\b', r'\bmistake\b', r'\bfix\b',
]

NEGATION_PATTERNS_RU = [
    r'\bбольше не\b', r'\bуже не\b', r'\bне работает\b',
    r'\bизменил(?:ся)?\b', r'\bобновил(?:ся)?\b', r'\bобновлено\b',
    r'\bтеперь\b', r'\bсейчас\b',
    r'\bраньше\b', r'\bпрежде\b', r'\bбыл(?:о)?\b',
    r'\bзаменил(?:ся)?\b', r'\bперешёл\b', r'\bпереехал\b',
    r'\bне используем\b', r'\bотказал(?:ся)?\b',
    r'\bисправлено\b', r'\bошибка\b', r'\bна самом деле\b',
    r'\bпо факту\b', r'\bна самом деле\b',
]

ALL_NEGATION_PATTERNS = NEGATION_PATTERNS_EN + NEGATION_PATTERNS_RU
_compiled = [re.compile(p, re.IGNORECASE) for p in ALL_NEGATION_PATTERNS]


def has_contradiction_signal(text: str) -> Tuple[bool, List[str]]:
    """Check if text contains contradiction/update signals.

    Returns (has_signal, matched_patterns)
    """
    matched = []
    for pattern in _compiled:
        if pattern.search(text):
            matched.append(pattern.pattern)
    return len(matched) > 0, matched


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two embedding vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def find_contradictions(
    db_path: str,
    similarity_threshold: float = 0.72,
    window_size: int = 100,
) -> List[Dict]:
    """
    Find pairs of notes that may contradict each other.

    Strategy:
    - Load all notes with embeddings
    - Sliding window comparison (O(n * window) instead of O(n^2))
    - For each pair with similarity > threshold:
        - Check if either note has contradiction signals
        - If yes -> potential contradiction
    - Sort by severity (similarity * signal strength)

    Returns list of contradiction dicts.
    """
    conn = sqlite3.connect(db_path)
    rows = conn.execute("""
        SELECT id, content, embedding, timestamp, category, importance
        FROM nodes
        WHERE embedding IS NOT NULL
        ORDER BY timestamp ASC
    """).fetchall()
    conn.close()

    if len(rows) < 2:
        return []

    # Parse embeddings
    notes = []
    for nid, content, emb_blob, ts, cat, importance in rows:
        try:
            emb = np.frombuffer(emb_blob, dtype=np.float32).copy()
            notes.append({
                'id': nid,
                'content': content or '',
                'embedding': emb,
                'timestamp': ts or '',
                'category': cat or '',
                'importance': importance or 'normal',
            })
        except Exception:
            continue

    contradictions = []
    n = len(notes)

    for i in range(n):
        a = notes[i]
        # Compare with next `window_size` notes (temporal proximity)
        for j in range(i + 1, min(i + 1 + window_size, n)):
            b = notes[j]

            # Skip same category pairs that are just continuations
            # (temporal chains, not contradictions)
            # But keep if content signals change
            sim = cosine_similarity(a['embedding'], b['embedding'])
            if sim < similarity_threshold:
                continue

            # Check for contradiction signals in either note
            sig_a, patterns_a = has_contradiction_signal(a['content'])
            sig_b, patterns_b = has_contradiction_signal(b['content'])

            if not (sig_a or sig_b):
                continue

            # Determine which is newer (potential superseder)
            if a['timestamp'] <= b['timestamp']:
                older, newer = a, b
                older_patterns = patterns_a
                newer_patterns = patterns_b
            else:
                older, newer = b, a
                older_patterns = patterns_b
                newer_patterns = patterns_a

            # Severity: higher similarity + more signals = more likely contradiction
            signal_count = len(patterns_a) + len(patterns_b)
            severity = sim * min(signal_count / 3.0, 1.0)

            contradictions.append({
                'older_id': older['id'],
                'newer_id': newer['id'],
                'similarity': round(sim, 4),
                'severity': round(severity, 4),
                'older_category': older['category'],
                'newer_category': newer['category'],
                'older_snippet': older['content'][:120],
                'newer_snippet': newer['content'][:120],
                'signals': list(set(older_patterns + newer_patterns))[:5],
                'older_importance': older['importance'],
                'newer_importance': newer['importance'],
            })

    # Sort by severity descending
    contradictions.sort(key=lambda x: x['severity'], reverse=True)
    return contradictions


def run_contradiction_detection(
    db_path: str,
    similarity_threshold: float = 0.72,
    window_size: int = 100,
    dry_run: bool = False,
) -> Dict:
    """
    Run contradiction detection and store results.

    Stores in contradiction_log table:
      - older_node_id, newer_node_id
      - similarity, severity
      - signals (matched patterns)
      - status: 'pending' (human reviews), 'resolved', 'false_positive'

    NEVER modifies or deletes notes. Report only.
    Human decides what to do.
    """
    print(f"  Similarity threshold: {similarity_threshold}, window: {window_size}")

    contradictions = find_contradictions(
        db_path,
        similarity_threshold=similarity_threshold,
        window_size=window_size,
    )

    print(f"  Found {len(contradictions)} potential contradictions")

    if not contradictions:
        return {'found': 0, 'stored': 0}

    # Show top 5
    for c in contradictions[:5]:
        print(f"    #{c['older_id']} <-> #{c['newer_id']} "
              f"sim={c['similarity']} sev={c['severity']} "
              f"[{c['older_category']}]")
        print(f"      older: {c['older_snippet'][:60]}...")
        print(f"      newer: {c['newer_snippet'][:60]}...")

    if dry_run:
        return {'found': len(contradictions), 'stored': 0, 'details': contradictions[:10]}

    # Store in DB
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contradiction_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            older_node_id INTEGER NOT NULL,
            newer_node_id INTEGER NOT NULL,
            similarity REAL,
            severity REAL,
            signals TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            resolved_at TEXT,
            notes TEXT,
            FOREIGN KEY (older_node_id) REFERENCES nodes(id) ON DELETE CASCADE,
            FOREIGN KEY (newer_node_id) REFERENCES nodes(id) ON DELETE CASCADE
        )
    """)

    # Index for fast lookup
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_contradiction_nodes
        ON contradiction_log(older_node_id, newer_node_id)
    """)
    conn.commit()

    stored = 0
    now = datetime.now().isoformat()
    for c in contradictions:
        # Only store if not already logged (same pair)
        existing = conn.execute("""
            SELECT id FROM contradiction_log
            WHERE older_node_id=? AND newer_node_id=?
            AND status != 'false_positive'
        """, (c['older_id'], c['newer_id'])).fetchone()

        if existing:
            continue

        signals_str = '; '.join(c['signals'])
        conn.execute("""
            INSERT INTO contradiction_log
            (older_node_id, newer_node_id, similarity, severity, signals, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, (
            c['older_id'], c['newer_id'],
            c['similarity'], c['severity'],
            signals_str, now
        ))
        stored += 1

    conn.commit()
    conn.close()

    print(f"  Stored {stored} new contradiction pairs (status=pending)")
    print(f"  Review via: SELECT * FROM contradiction_log WHERE status='pending' ORDER BY severity DESC;")

    return {
        'found': len(contradictions),
        'stored': stored,
        'details': contradictions[:10],
    }