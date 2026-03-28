#!/usr/bin/env python3
"""
Query Temporal Decomposition for HippoGraph

Detects temporal signal words in queries and decomposes them into:
- content_query: semantic part for embedding search
- temporal_query: temporal part for date-range matching

Zero LLM cost - pure regex/pattern matching.

March 27 2026: Added metric/state query detection.
Queries like "what is the consciousness score" are implicitly temporal --
they always ask for the CURRENT value, not a historical one.
Such queries get is_temporal=True with direction="after" (prefer newer notes).
"""
import re
from typing import Tuple, Optional

# Temporal signal patterns that indicate temporal intent
TEMPORAL_SIGNAL_WORDS = [
    # English - when/ordering
    r'\bwhen\s+did\b', r'\bwhen\s+was\b', r'\bwhen\s+is\b', r'\bwhen\s+will\b',
    r'\bhow\s+long\s+ago\b', r'\bhow\s+long\s+since\b',
    r'\bbefore\b', r'\bafter\b', r'\bduring\b',
    r'\bfirst\s+time\b', r'\blast\s+time\b', r'\bmost\s+recent\b',
    r'\bearlier\b', r'\blater\b', r'\bpreviously\b',
    r'\brecently\b', r'\blatest\b',
    # English - explicit current/now
    r'\bcurrent\b', r'\bcurrently\b', r'\bright\s+now\b', r'\btoday\b',
    r'\bactual\b', r'\bup.to.date\b', r'\bup\s+to\s+date\b',
    # English - temporal ordering
    r'\bwhat\s+happened\s+(before|after|first|next)\b',
    r'\bwhat\s+did\s+\w+\s+do\s+(before|after|first|next)\b',
    r'\bin\s+what\s+order\b', r'\bchronological\b',
    r'\bwhich\s+came\s+(first|last)\b',
    # Russian - time
    r'\b\u043a\u043e\u0433\u0434\u0430\b', r'\b\u0434\u043e\s+\u0442\u043e\u0433\u043e\b', r'\b\u043f\u043e\u0441\u043b\u0435\s+\u0442\u043e\u0433\u043e\b',
    r'\b\u0441\u043d\u0430\u0447\u0430\u043b\u0430\b', r'\b\u043f\u043e\u0442\u043e\u043c\b', r'\b\u043d\u0435\u0434\u0430\u0432\u043d\u043e\b',
    r'\b\u0432\s+\u043a\u0430\u043a\u043e\u043c\s+\u043f\u043e\u0440\u044f\u0434\u043a\u0435\b', r'\b\u0440\u0430\u043d\u044c\u0448\u0435\b', r'\b\u043f\u043e\u0437\u0436\u0435\b',
    # Russian - explicit current/now
    r'\b\u0442\u0435\u043a\u0443\u0449\u0438\u0439\b', r'\b\u0442\u0435\u043a\u0443\u0449\u0430\u044f\b', r'\b\u0441\u0435\u0439\u0447\u0430\u0441\b', r'\b\u0430\u043a\u0442\u0443\u0430\u043b\u044c\u043d\u044b\u0439\b', r'\b\u0430\u043a\u0442\u0443\u0430\u043b\u044c\u043d\u043e\b',
]

# Metric/state signal patterns - queries implicitly asking for CURRENT value
# These are semantically temporal even without explicit time words:
# "what is X" where X is a measurable/changing property
METRIC_SIGNAL_PATTERNS = [
    # "what is [the] [words] score/result/value/percent/composite/recall"
    r'\bwhat\s+is\s+(the\s+)?[\w\s]+(score|result|value|percent|composite|rate|metric|level|recall)\b',
    # "what is [the] current/latest/actual X"
    r'\bwhat\s+is\s+(the\s+)?(current|latest|actual)\b',
    # Specific metric domain keywords - inherently change over time
    r'\b(consciousness|emotional_modulation|global_workspace|benchmark|locomo|pcb|continuity)\b',
    # Any "what is X benchmark/locomo/pcb" pattern
    r'\bwhat\s+is\s+[\w\s]+(benchmark|locomo|pcb)[\w\s]*\b',
    # Russian: "какой результат" / "каков результат"
    r'\bкако(й|в)\s+[\w\s]*результат\b',
]

# Words to strip from query to get clean content query
TEMPORAL_STRIP_PATTERNS = [
    r'\bwhen\s+did\b', r'\bwhen\s+was\b', r'\bwhen\s+is\b',
    r'\bhow\s+long\s+ago\s+did\b', r'\bhow\s+long\s+since\b',
    r'\bwhat\s+happened\s+(before|after)\b',
    r'\bin\s+what\s+order\s+did\b',
    r'\bwhich\s+came\s+(first|last)\b',
    r'\bbefore\s+or\s+after\b',
    r'\b\u043a\u043e\u0433\u0434\u0430\b',
    # Strip explicit current/now words (they don't add semantic content)
    r'\bcurrent\b', r'\bcurrently\b', r'\bactual\b', r'\bup-to-date\b',
    r'\b\u0442\u0435\u043a\u0443\u0449\u0438\u0439\b', r'\b\u0442\u0435\u043a\u0443\u0449\u0430\u044f\b', r'\b\u0430\u043a\u0442\u0443\u0430\u043b\u044c\u043d\u044b\u0439\b',
]


def is_metric_query(query: str) -> bool:
    """
    Detect queries that implicitly ask for a CURRENT/LATEST value.

    These are semantically temporal even without explicit time words:
    - "What is the consciousness composite score?" -> wants latest
    - "What is LOCOMO Recall@5?" -> wants latest benchmark result
    - "What is emotional modulation?" -> wants current measurement

    Returns True if query pattern suggests a measurable, changing property.
    """
    q_lower = query.lower()
    for pattern in METRIC_SIGNAL_PATTERNS:
        if re.search(pattern, q_lower):
            return True
    return False


def is_temporal_query(query: str) -> bool:
    """Check if query has temporal intent (explicit or implicit via metric)."""
    q_lower = query.lower()
    for pattern in TEMPORAL_SIGNAL_WORDS:
        if re.search(pattern, q_lower):
            return True
    if is_metric_query(query):
        return True
    return False


def decompose_temporal_query(query: str) -> Tuple[str, bool, Optional[str]]:
    """
    Decompose query into content and temporal parts.

    Returns:
        (content_query, is_temporal, temporal_direction)

        content_query: cleaned query for semantic search
        is_temporal: whether temporal intent detected
        temporal_direction: "before", "after", "when", "order", or None

    March 27 2026: metric queries get direction="after" (prefer newer notes).
    This solves the case where an old note with high PageRank beats a newer
    note with the actual current value of a metric.
    """
    q_lower = query.lower().strip()

    if not is_temporal_query(query):
        return query, False, None

    # Check if this is a metric query (implicit temporal, prefer newer)
    metric_query = is_metric_query(query)

    # Detect temporal direction
    direction = None
    if re.search(r'\bbefore\b|\u0434\u043e\s+\u0442\u043e\u0433\u043e|\u0440\u0430\u043d\u044c\u0448\u0435|earlier|previously|first', q_lower):
        direction = "before"
    elif re.search(r'\bafter\b|\u043f\u043e\u0441\u043b\u0435\s+\u0442\u043e\u0433\u043e|\u043f\u043e\u0437\u0436\u0435|later|next|then', q_lower):
        direction = "after"
    elif re.search(r'\border\b|\u043f\u043e\u0440\u044f\u0434\u043a|chronolog|sequence', q_lower):
        direction = "order"
    elif metric_query:
        # Metric queries without explicit direction -> prefer newer (after)
        direction = "after"
    else:
        direction = "when"

    # Strip temporal signal words to get clean content query
    content_query = query
    for pattern in TEMPORAL_STRIP_PATTERNS:
        content_query = re.sub(pattern, '', content_query, flags=re.IGNORECASE)

    # Clean up extra whitespace and punctuation
    content_query = re.sub(r'\s+', ' ', content_query).strip()
    content_query = re.sub(r'^[\s,\?\!\.]+|[\s,\?\!\.]+$', '', content_query).strip()

    # If stripping removed too much, fall back to original
    if len(content_query) < 5:
        content_query = query

    return content_query, True, direction


def compute_temporal_order_score(note_timestamp: str, direction: str,
                                 all_timestamps: list) -> float:
    """
    Score notes based on temporal ordering.
    For 'before' queries: prefer earlier notes.
    For 'after' queries: prefer later notes (including metric queries).
    For 'when'/'order': prefer notes with temporal data, slight recency bias.

    Returns 0.0 to 1.0 score.
    """
    from datetime import datetime
    try:
        note_ts = datetime.fromisoformat(note_timestamp)
    except (ValueError, TypeError):
        return 0.0

    if not all_timestamps:
        return 0.5

    # Parse all timestamps
    parsed = []
    for ts in all_timestamps:
        try:
            parsed.append(datetime.fromisoformat(ts))
        except (ValueError, TypeError):
            continue

    if not parsed:
        return 0.5

    min_ts = min(parsed)
    max_ts = max(parsed)
    total_range = (max_ts - min_ts).total_seconds()

    if total_range == 0:
        return 0.5

    # Normalize position: 0.0 = earliest, 1.0 = latest
    position = (note_ts - min_ts).total_seconds() / total_range

    if direction == "before":
        # Prefer earlier notes
        return 1.0 - position
    elif direction == "after":
        # Prefer later notes (also used for metric queries)
        return position
    else:
        # "when" / "order" - slight boost for having temporal data, no ordering preference
        return 0.5