#!/usr/bin/env python3
"""
Query Temporal Decomposition for HippoGraph

Detects temporal signal words in queries and decomposes them into:
- content_query: semantic part for embedding search
- temporal_query: temporal part for date-range matching

Zero LLM cost — pure regex/pattern matching.
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
    # English - temporal ordering
    r'\bwhat\s+happened\s+(before|after|first|next)\b',
    r'\bwhat\s+did\s+\w+\s+do\s+(before|after|first|next)\b',
    r'\bin\s+what\s+order\b', r'\bchronological\b',
    r'\bwhich\s+came\s+(first|last)\b',
    # Russian
    r'\bкогда\b', r'\bдо\s+того\b', r'\bпосле\s+того\b',
    r'\bсначала\b', r'\bпотом\b', r'\bнедавно\b',
    r'\bв\s+каком\s+порядке\b', r'\bраньше\b', r'\bпозже\b',
]

# Words to strip from query to get clean content query
TEMPORAL_STRIP_PATTERNS = [
    r'\bwhen\s+did\b', r'\bwhen\s+was\b', r'\bwhen\s+is\b',
    r'\bhow\s+long\s+ago\s+did\b', r'\bhow\s+long\s+since\b',
    r'\bwhat\s+happened\s+(before|after)\b',
    r'\bin\s+what\s+order\s+did\b',
    r'\bwhich\s+came\s+(first|last)\b',
    r'\bbefore\s+or\s+after\b',
    r'\bкогда\b',
]


def is_temporal_query(query: str) -> bool:
    """Check if query has temporal intent."""
    q_lower = query.lower()
    for pattern in TEMPORAL_SIGNAL_WORDS:
        if re.search(pattern, q_lower):
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
    """
    q_lower = query.lower().strip()
    
    if not is_temporal_query(query):
        return query, False, None
    
    # Detect temporal direction
    direction = None
    if re.search(r'\bbefore\b|до\s+того|раньше|earlier|previously|first', q_lower):
        direction = "before"
    elif re.search(r'\bafter\b|после\s+того|позже|later|next|then', q_lower):
        direction = "after"
    elif re.search(r'\border\b|порядк|chronolog|sequence', q_lower):
        direction = "order"
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
    For 'after' queries: prefer later notes.
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
        # Prefer later notes
        return position
    else:
        # "when" / "order" — slight boost for having temporal data, no ordering preference
        return 0.5
