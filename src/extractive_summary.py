"""
Extractive Summary for Memory Clusters

For each cluster of semantically related notes, finds the single note
that best represents the entire cluster.

Algorithm:
  1. TF-IDF across all notes in cluster -> key terms
  2. Score each note by coverage of top terms
  3. Weight by intra-cluster PageRank (most connected note)
  4. Best note = highest combined score -> cluster representative

Zero LLM cost. Pure math: numpy + collections.
Original notes preserved intact — no compression, no deletion.

CJK support: Chinese text is segmented via jieba (if installed).
Japanese/Korean work via char-level Unicode regex.
Set ENABLE_CJK=false to disable jieba even if installed.
"""
import sqlite3
import math
import re
import os
import numpy as np
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# CJK word segmentation — optional, graceful fallback if not installed
# jieba (MIT) for Chinese; Japanese/Korean use char-level via _TOKEN_RE
# Set ENABLE_CJK=false in .env to disable even if jieba is installed
_JIEBA_AVAILABLE = False
_CJK_ENABLED = os.environ.get('ENABLE_CJK', 'true').lower() != 'false'

if _CJK_ENABLED:
    try:
        import jieba
        jieba.setLogLevel(20)  # suppress jieba init messages
        _JIEBA_AVAILABLE = True
    except ImportError:
        pass  # fallback to char-level tokenization

# Regex to detect CJK characters in text

# Stopwords for major languages supported by xx_ent_wiki_sm
_STOPWORDS = {
    # English
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'to', 'of', 'in', 'for',
    'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'and',
    'but', 'or', 'not', 'no', 'so', 'if', 'then', 'that', 'this', 'it',
    'its', 'i', 'we', 'you', 'he', 'she', 'they', 'my', 'our', 'your',
    # Russian (русский)
    'и', 'в', 'на', 'с', 'по', 'из', 'за', 'к', 'о', 'от', 'до',
    'не', 'что', 'как', 'это', 'но', 'а', 'или', 'же', 'ли', 'бы',
    'то', 'для', 'при', 'об', 'со', 'без', 'под', 'над', 'про',
    'его', 'её', 'им', 'их', 'мне', 'мы', 'вы', 'они', 'есть', 'был',
    # German (Deutsch)
    'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einer',
    'und', 'oder', 'aber', 'nicht', 'mit', 'bei', 'von', 'aus', 'nach',
    'zu', 'zum', 'zur', 'im', 'am', 'ist', 'sind', 'war', 'hat', 'ich',
    'du', 'er', 'sie', 'wir', 'ihr', 'es', 'sich', 'auf', 'an', 'in',
    # Spanish (español)
    'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del',
    'al', 'en', 'con', 'por', 'para', 'que', 'se', 'su', 'sus', 'les',
    'como', 'pero', 'hay', 'está', 'están', 'son', 'fue', 'han', 'yo',
    'tu', 'nos', 'vos', 'este', 'esta', 'estos', 'estas', 'ese', 'eso',
    # French (français)
    'le', 'les', 'un', 'une', 'des', 'du', 'au', 'aux', 'et', 'ou',
    'en', 'dans', 'sur', 'avec', 'par', 'pour', 'ne', 'pas', 'plus',
    'que', 'qui', 'se', 'ce', 'son', 'ses', 'mon', 'mes', 'il', 'elle',
    'nous', 'vous', 'ils', 'elles', 'est', 'sont', 'avoir', 'je', 'tu',
    # Portuguese (português)
    'de', 'da', 'do', 'das', 'dos', 'em', 'na', 'no', 'nas', 'nos',
    'um', 'uma', 'que', 'se', 'por', 'para', 'com', 'como', 'mais',
    'é', 'ao', 'à', 'ou', 'mas', 'foi', 'ele', 'ela', 'seu', 'sua',
    # Italian (italiano)
    'il', 'lo', 'la', 'gli', 'le', 'un', 'uno', 'una', 'di', 'del',
    'della', 'dei', 'degli', 'delle', 'in', 'nel', 'nella', 'nei',
    'che', 'con', 'per', 'non', 'su', 'ma', 'è', 'sono', 'io', 'tu',
    # Chinese stopwords (中文)
    '的', '了', '在', '是', '我', '不', '他', '这', '中', '大', '来', '上', '个',
    '和', '到', '说', '为', '就', '以', '人', '都', '而', '可', '于', '及', '与',
    '就', '她', '我们', '一个', '有', '这个', '对', '那', '要', '也', '这些',
    # Japanese stopwords (日本語)
    'の', 'に', 'は', 'を', 'が', 'で', 'と', 'も', 'や', 'か', 'から',
    'です', 'ます', 'だ', 'だった', 'である', 'します', 'れる', 'される',
}

# Unicode token pattern: captures Latin, Cyrillic, CJK, Arabic, Hebrew,
# Devanagari, Thai, Korean, Greek, and more.
_TOKEN_RE = re.compile(
    r'['
    r'\w'           # word chars (ASCII + Unicode letters/digits/_)
    r'\u0400-\u04FF'  # Cyrillic
    r'\u4E00-\u9FFF'  # CJK Unified Ideographs
    r'\u3040-\u30FF'  # Hiragana + Katakana
    r'\uAC00-\uD7AF'  # Hangul
    r'\u0600-\u06FF'  # Arabic
    r'\u0900-\u097F'  # Devanagari
    r'\u0E00-\u0E7F'  # Thai
    r'\u0370-\u03FF'  # Greek
    r']+',
    re.UNICODE
)

# Detects text that contains Chinese/Japanese/Korean characters
_CJK_DETECT_RE = re.compile(
    r'[一-鿿぀-ヿ가-힯]'
)


def _tokenize_cjk(text: str) -> List[str]:
    """
    CJK-aware tokenizer.
    - Chinese segments: jieba (if available) or char-level fallback
    - Non-CJK portions (Latin, Cyrillic, etc): standard _TOKEN_RE
    - Hiragana/Katakana/Hangul: char-level via _TOKEN_RE
    """
    tokens = []

    if _JIEBA_AVAILABLE:
        # Split text into CJK and non-CJK spans
        # Use a simple split: find consecutive CJK blocks and non-CJK blocks
        parts = re.split(r'([\u4E00-\u9FFF\u3400-\u4DBF\uF900-\uFAFF]+)', text)
        for part in parts:
            if not part:
                continue
            if re.match(r'^[\u4E00-\u9FFF\u3400-\u4DBF\uF900-\uFAFF]+$', part):
                # Chinese block -> jieba segmentation
                tokens.extend(jieba.lcut(part))
            else:
                # Non-Chinese (Latin, Cyrillic, Hiragana, Katakana, etc)
                tokens.extend(_TOKEN_RE.findall(part.lower()))
    else:
        # No jieba: char-level for everything
        tokens.extend(_TOKEN_RE.findall(text.lower()))

    return [
        t.lower() for t in tokens
        if t not in _STOPWORDS and len(t) > 1
    ]


def _tokenize(text: str) -> List[str]:
    """Unicode-aware tokenizer supporting 50+ languages.
    Routes CJK text through jieba segmentation when available.
    """
    if _CJK_ENABLED and _CJK_DETECT_RE.search(text):
        return _tokenize_cjk(text)

    text = text.lower()
    tokens = _TOKEN_RE.findall(text)
    return [
        t for t in tokens
        if t not in _STOPWORDS and len(t) > 1
    ]


def compute_tfidf(docs: List[List[str]]) -> List[Dict[str, float]]:
    """Compute TF-IDF for list of tokenized documents."""
    n = len(docs)
    if n == 0:
        return []

    # Document frequency
    df = Counter()
    for doc in docs:
        for term in set(doc):
            df[term] += 1

    tfidf_docs = []
    for doc in docs:
        tf = Counter(doc)
        total = len(doc) or 1
        scores = {}
        for term, count in tf.items():
            tf_score = count / total
            idf_score = math.log((n + 1) / (df[term] + 1)) + 1
            scores[term] = tf_score * idf_score
        tfidf_docs.append(scores)

    return tfidf_docs


def intra_cluster_pagerank(
    node_ids: List[int],
    embeddings: Dict[int, np.ndarray],
    damping: float = 0.85,
    iterations: int = 20,
    threshold: float = 0.65,
) -> Dict[int, float]:
    """PageRank within the cluster based on embedding similarity."""
    n = len(node_ids)
    if n <= 1:
        return {nid: 1.0 for nid in node_ids}

    # Build adjacency weights
    adj = defaultdict(dict)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = node_ids[i], node_ids[j]
            ea, eb = embeddings.get(a), embeddings.get(b)
            if ea is None or eb is None:
                continue
            sim = float(np.dot(ea, eb) / (np.linalg.norm(ea) * np.linalg.norm(eb) + 1e-9))
            if sim >= threshold:
                adj[a][b] = sim
                adj[b][a] = sim

    # Normalise outgoing weights
    for nid in node_ids:
        total = sum(adj[nid].values()) or 1.0
        for nb in adj[nid]:
            adj[nid][nb] /= total

    # Power iteration
    pr = {nid: 1.0 / n for nid in node_ids}
    for _ in range(iterations):
        new_pr = {}
        for nid in node_ids:
            rank = (1 - damping) / n
            for nb in node_ids:
                if nid in adj[nb]:
                    rank += damping * adj[nb][nid] * pr[nb]
            new_pr[nid] = rank
        pr = new_pr

    return pr


def find_cluster_representative(
    cluster_ids: List[int],
    contents: Dict[int, str],
    embeddings: Dict[int, np.ndarray],
    top_terms: int = 20,
    pagerank_weight: float = 0.4,
    tfidf_weight: float = 0.6,
) -> Tuple[int, List[str], float]:
    """
    Find the best representative note for a cluster.

    Returns:
        (representative_note_id, top_terms_list, score)
    """
    if len(cluster_ids) == 1:
        tokens = _tokenize(contents.get(cluster_ids[0], ''))
        return cluster_ids[0], list(set(tokens))[:top_terms], 1.0

    # Tokenize
    tokenized = {nid: _tokenize(contents.get(nid, '')) for nid in cluster_ids}
    docs = [tokenized[nid] for nid in cluster_ids]

    # TF-IDF
    tfidf = compute_tfidf(docs)
    tfidf_by_id = {nid: tfidf[i] for i, nid in enumerate(cluster_ids)}

    # Cluster-level top terms (sum TF-IDF across all docs)
    term_totals = Counter()
    for scores in tfidf:
        for term, score in scores.items():
            term_totals[term] += score
    cluster_top_terms = [t for t, _ in term_totals.most_common(top_terms)]

    # Coverage score: how well does this note cover cluster top terms?
    coverage = {}
    for nid in cluster_ids:
        doc_terms = set(tfidf_by_id[nid].keys())
        hits = sum(1 for t in cluster_top_terms if t in doc_terms)
        coverage[nid] = hits / (len(cluster_top_terms) or 1)

    # Intra-cluster PageRank
    pr = intra_cluster_pagerank(cluster_ids, embeddings)
    # Normalise PR to [0, 1]
    pr_max = max(pr.values()) or 1.0
    pr_norm = {nid: v / pr_max for nid, v in pr.items()}

    # Combined score
    combined = {
        nid: tfidf_weight * coverage[nid] + pagerank_weight * pr_norm[nid]
        for nid in cluster_ids
    }
    best = max(combined, key=lambda x: combined[x])
    return best, cluster_top_terms, combined[best]


def run_extractive_summaries(
    db_path: str,
    clusters: List[List[int]],
    dry_run: bool = False,
) -> Dict:
    """
    For each cluster, find representative note and store summary metadata.

    Stores in node metadata (JSON field or separate table):
      - cluster_id (hash of sorted node ids)
      - is_cluster_representative = True
      - cluster_top_terms (comma-separated)
      - cluster_size

    Returns stats dict.
    """
    conn = sqlite3.connect(db_path)

    # Ensure cluster_summaries table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cluster_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cluster_hash TEXT UNIQUE,
            representative_node_id INTEGER,
            cluster_size INTEGER,
            top_terms TEXT,
            score REAL,
            created_at TEXT,
            FOREIGN KEY (representative_node_id) REFERENCES nodes(id) ON DELETE SET NULL
        )
    """)
    conn.commit()

    # Load all content + embeddings needed
    all_ids = list({nid for cluster in clusters for nid in cluster})
    if not all_ids:
        conn.close()
        return {'clusters': 0, 'representatives': 0, 'skipped': 0}

    placeholders = ','.join('?' * len(all_ids))
    rows = conn.execute(
        f"SELECT id, content, embedding FROM nodes WHERE id IN ({placeholders})",
        all_ids
    ).fetchall()

    contents = {r[0]: r[1] or '' for r in rows}
    embeddings = {}
    for r in rows:
        if r[2]:
            try:
                embeddings[r[0]] = np.frombuffer(r[2], dtype=np.float32).copy()
            except Exception:
                pass

    conn.close()

    stats = {'clusters': len(clusters), 'representatives': 0, 'skipped': 0, 'details': []}
    now = datetime.now().isoformat()

    for cluster in clusters:
        if len(cluster) < 2:
            stats['skipped'] += 1
            continue

        # Cluster hash = sorted ids joined
        cluster_hash = '_'.join(str(x) for x in sorted(cluster))

        try:
            rep_id, top_terms, score = find_cluster_representative(
                cluster, contents, embeddings
            )
        except Exception as e:
            stats['skipped'] += 1
            print(f"  Warning: cluster {cluster_hash[:20]}... skipped: {e}")
            continue

        terms_str = ','.join(top_terms[:15])

        if not dry_run:
            conn2 = sqlite3.connect(db_path)
            conn2.execute("""
                INSERT OR REPLACE INTO cluster_summaries
                (cluster_hash, representative_node_id, cluster_size, top_terms, score, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cluster_hash, rep_id, len(cluster), terms_str, score, now))
            conn2.commit()
            conn2.close()

        stats['representatives'] += 1
        stats['details'].append({
            'rep_id': rep_id,
            'cluster_size': len(cluster),
            'top_terms': top_terms[:5],
            'score': round(score, 3),
        })

    # Print summary
    cjk_status = f"jieba={'on' if _JIEBA_AVAILABLE else 'fallback(char-level)'}"
    print(f"  Clusters processed: {stats['clusters']} [{cjk_status}]")
    print(f"  Representatives found: {stats['representatives']}")
    print(f"  Skipped: {stats['skipped']}")
    if stats['details']:
        print("  Top clusters by size:")
        top = sorted(stats['details'], key=lambda x: x['cluster_size'], reverse=True)[:3]
        for d in top:
            print(f"    #{d['rep_id']} represents {d['cluster_size']} notes | "
                  f"terms: {', '.join(d['top_terms'][:3])} | score={d['score']}")

    return stats