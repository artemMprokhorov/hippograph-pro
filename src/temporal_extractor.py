#!/usr/bin/env python3
"""
Temporal Expression Extractor for HippoGraph Bi-Temporal Model

Extracts and resolves temporal expressions from text to absolute dates.
Supports both explicit dates and relative expressions.

Design principle: "Time is a helper, not a jailer" — nullable results
for notes without temporal content (reflections, emotions, etc.)
"""
import re
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple


# Relative time patterns (English)
RELATIVE_PATTERNS_EN = [
    # "last/next/this + period"
    (r'\b(last|previous)\s+(week|month|year|summer|winter|spring|fall|autumn|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', 'relative_past'),
    (r'\b(next|coming)\s+(week|month|year|summer|winter|spring|fall|autumn|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', 'relative_future'),
    (r'\b(this)\s+(week|month|year|morning|afternoon|evening)\b', 'relative_current'),
    # "N days/weeks/months ago"
    (r'\b(\d+)\s+(days?|weeks?|months?|years?|hours?)\s+ago\b', 'relative_ago'),
    # "yesterday", "today", "tomorrow"
    (r'\b(yesterday|today|tomorrow|tonight)\b', 'relative_day'),
    # "in October", "in 2024", "in January 2025"
    (r'\bin\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s*(\d{4})?\b', 'month_ref'),
    # "on Monday", "on the 5th"
    (r'\bon\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', 'day_of_week'),
]

# Relative time patterns (Russian)
RELATIVE_PATTERNS_RU = [
    (r'\b(прошл[аоуюые][йемг]?|предыдущ[аоуюые][йемг]?)\s+(недел[юиье]|месяц[еа]?|год[уа]?|лет[оа]?|зим[уыеа]|весн[уыеа]|осен[ьюи])\b', 'relative_past'),
    (r'\b(следующ[аоуюые][йемг]?|будущ[аоуюые][йемг]?)\s+(недел[юиье]|месяц[еа]?|год[уа]?)\b', 'relative_future'),
    (r'\b(\d+)\s+(дн[яейь]|недел[ьюией]|месяц[евао]?|год[аов]?|час[аов]?)\s+назад\b', 'relative_ago'),
    (r'\b(вчера|сегодня|завтра|позавчера)\b', 'relative_day'),
    (r'\bв\s+(январ[еяю]|феврал[еяю]|март[еа]?|апрел[еяю]|ма[еяю]|июн[еяю]|июл[еяю]|август[еа]?|сентябр[еяю]|октябр[еяю]|ноябр[еяю]|декабр[еяю])\s*(\d{4})?\b', 'month_ref'),
]

# Explicit date patterns
EXPLICIT_DATE_PATTERNS = [
    # ISO: 2025-01-15
    (r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', 'iso_date'),
    # US: 01/15/2025 or 1/15/2025
    (r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', 'us_date'),
    # Written: January 15, 2025 or Jan 15, 2025
    (r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s*(\d{4})\b', 'written_date'),
    # Written: 15 January 2025
    (r'\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b', 'written_date_eu'),
]

MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
    'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}

MONTH_MAP_RU = {
    'январ': 1, 'феврал': 2, 'март': 3, 'апрел': 4,
    'ма': 5, 'июн': 6, 'июл': 7, 'август': 8,
    'сентябр': 9, 'октябр': 10, 'ноябр': 11, 'декабр': 12,
}

DAY_MAP = {
    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
    'friday': 4, 'saturday': 5, 'sunday': 6,
}

SEASON_RANGES = {
    'summer': (6, 8), 'winter': (12, 2), 'spring': (3, 5),
    'fall': (9, 11), 'autumn': (9, 11),
    'лет': (6, 8), 'зим': (12, 2), 'весн': (3, 5), 'осен': (9, 11),
}


def resolve_relative_day(expression: str, reference_date: datetime) -> Tuple[datetime, datetime]:
    """Resolve yesterday/today/tomorrow to date range."""
    expr = expression.lower().strip()
    if expr in ('yesterday', 'вчера'):
        d = reference_date - timedelta(days=1)
    elif expr in ('today', 'сегодня', 'tonight'):
        d = reference_date
    elif expr in ('tomorrow', 'завтра'):
        d = reference_date + timedelta(days=1)
    elif expr in ('позавчера',):
        d = reference_date - timedelta(days=2)
    else:
        return reference_date, reference_date
    return d.replace(hour=0, minute=0, second=0), d.replace(hour=23, minute=59, second=59)


def resolve_relative_ago(amount: int, unit: str, reference_date: datetime) -> Tuple[datetime, datetime]:
    """Resolve 'N days/weeks/months ago' to date range."""
    unit = unit.lower().rstrip('s')  # normalize plural
    if unit in ('day', 'дн', 'день'):
        delta = timedelta(days=amount)
        d = reference_date - delta
        return d.replace(hour=0, minute=0, second=0), d.replace(hour=23, minute=59, second=59)
    elif unit in ('week', 'недел'):
        delta = timedelta(weeks=amount)
        start = reference_date - delta
        end = start + timedelta(days=6)
        return start.replace(hour=0, minute=0, second=0), end.replace(hour=23, minute=59, second=59)
    elif unit in ('month', 'месяц'):
        month = reference_date.month - amount
        year = reference_date.year
        while month <= 0:
            month += 12
            year -= 1
        start = reference_date.replace(year=year, month=month, day=1, hour=0, minute=0, second=0)
        if month == 12:
            end = start.replace(year=year+1, month=1, day=1) - timedelta(seconds=1)
        else:
            end = start.replace(month=month+1, day=1) - timedelta(seconds=1)
        return start, end
    elif unit in ('year', 'год', 'лет'):
        year = reference_date.year - amount
        return datetime(year, 1, 1), datetime(year, 12, 31, 23, 59, 59)
    elif unit in ('hour', 'час'):
        delta = timedelta(hours=amount)
        d = reference_date - delta
        return d, d + timedelta(hours=1)
    return reference_date, reference_date


def resolve_month_ref(month_str: str, year: Optional[int], reference_date: datetime) -> Tuple[datetime, datetime]:
    """Resolve 'in October' or 'in January 2025' to date range."""
    month_lower = month_str.lower()
    month_num = MONTH_MAP.get(month_lower)
    if not month_num:
        # Try Russian month stems
        for stem, num in MONTH_MAP_RU.items():
            if month_lower.startswith(stem):
                month_num = num
                break
    if not month_num:
        return reference_date, reference_date
    
    if year is None:
        # Assume current or previous year based on whether month has passed
        if month_num > reference_date.month:
            year = reference_date.year - 1
        else:
            year = reference_date.year
    
    start = datetime(year, month_num, 1)
    if month_num == 12:
        end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end = datetime(year, month_num + 1, 1) - timedelta(seconds=1)
    return start, end


def resolve_season(season: str, direction: str, reference_date: datetime) -> Tuple[datetime, datetime]:
    """Resolve 'last summer', 'this winter' etc."""
    season_lower = season.lower()
    for key, (start_month, end_month) in SEASON_RANGES.items():
        if season_lower.startswith(key) or season_lower == key:
            if direction == 'relative_past':
                year = reference_date.year - 1 if start_month >= reference_date.month else reference_date.year
            elif direction == 'relative_future':
                year = reference_date.year + 1 if start_month <= reference_date.month else reference_date.year
            else:
                year = reference_date.year
            
            if start_month > end_month:  # winter wraps around
                start = datetime(year, start_month, 1)
                end = datetime(year + 1, end_month + 1, 1) - timedelta(seconds=1)
            else:
                start = datetime(year, start_month, 1)
                end = datetime(year, end_month + 1, 1) - timedelta(seconds=1)
            return start, end
    return reference_date, reference_date


def extract_temporal_expressions(text: str, reference_date: Optional[datetime] = None) -> Dict:
    """
    Extract and resolve temporal expressions from text.
    
    Returns:
        {
            "expressions": ["last week", "in October", ...],
            "t_event_start": "2025-10-01T00:00:00" or None,
            "t_event_end": "2025-10-31T23:59:59" or None
        }
    
    If multiple temporal expressions found, uses the most specific one.
    Returns None for t_event_* if no temporal expressions found (nullable by design).
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    text_lower = text.lower()
    found_expressions = []
    resolved_ranges = []
    
    # 1. Check explicit date patterns first (highest priority)
    for pattern, ptype in EXPLICIT_DATE_PATTERNS:
        for match in re.finditer(pattern, text_lower):
            try:
                if ptype == 'iso_date':
                    y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    dt = datetime(y, m, d)
                    found_expressions.append(match.group(0))
                    resolved_ranges.append((dt, dt.replace(hour=23, minute=59, second=59), 'explicit'))
                elif ptype == 'us_date':
                    m, d, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    dt = datetime(y, m, d)
                    found_expressions.append(match.group(0))
                    resolved_ranges.append((dt, dt.replace(hour=23, minute=59, second=59), 'explicit'))
                elif ptype == 'written_date':
                    m = MONTH_MAP.get(match.group(1))
                    d, y = int(match.group(2)), int(match.group(3))
                    if m:
                        dt = datetime(y, m, d)
                        found_expressions.append(match.group(0))
                        resolved_ranges.append((dt, dt.replace(hour=23, minute=59, second=59), 'explicit'))
                elif ptype == 'written_date_eu':
                    d = int(match.group(1))
                    m = MONTH_MAP.get(match.group(2))
                    y = int(match.group(3))
                    if m:
                        dt = datetime(y, m, d)
                        found_expressions.append(match.group(0))
                        resolved_ranges.append((dt, dt.replace(hour=23, minute=59, second=59), 'explicit'))
            except (ValueError, TypeError):
                continue

    
    # 2. Check relative patterns (English)
    for pattern, ptype in RELATIVE_PATTERNS_EN:
        for match in re.finditer(pattern, text_lower):
            expr = match.group(0)
            found_expressions.append(expr)
            try:
                if ptype == 'relative_day':
                    start, end = resolve_relative_day(match.group(1), reference_date)
                    resolved_ranges.append((start, end, 'relative'))
                elif ptype == 'relative_ago':
                    amount = int(match.group(1))
                    unit = match.group(2)
                    start, end = resolve_relative_ago(amount, unit, reference_date)
                    resolved_ranges.append((start, end, 'relative'))
                elif ptype == 'month_ref':
                    month_str = match.group(1)
                    year = int(match.group(2)) if match.group(2) else None
                    start, end = resolve_month_ref(month_str, year, reference_date)
                    resolved_ranges.append((start, end, 'relative'))
                elif ptype in ('relative_past', 'relative_future', 'relative_current'):
                    period = match.group(2)
                    if period in SEASON_RANGES:
                        start, end = resolve_season(period, ptype, reference_date)
                        resolved_ranges.append((start, end, 'relative'))
                    elif period == 'week':
                        if ptype == 'relative_past':
                            end = reference_date - timedelta(days=reference_date.weekday() + 1)
                            start = end - timedelta(days=6)
                        elif ptype == 'relative_future':
                            start = reference_date + timedelta(days=7 - reference_date.weekday())
                            end = start + timedelta(days=6)
                        else:
                            start = reference_date - timedelta(days=reference_date.weekday())
                            end = start + timedelta(days=6)
                        resolved_ranges.append((start.replace(hour=0,minute=0,second=0), end.replace(hour=23,minute=59,second=59), 'relative'))
                    elif period == 'month':
                        if ptype == 'relative_past':
                            first = reference_date.replace(day=1) - timedelta(days=1)
                            start = first.replace(day=1)
                            end = first
                        else:
                            start = reference_date.replace(day=1)
                            if start.month == 12:
                                end = start.replace(year=start.year+1, month=1, day=1) - timedelta(seconds=1)
                            else:
                                end = start.replace(month=start.month+1, day=1) - timedelta(seconds=1)
                        resolved_ranges.append((start.replace(hour=0,minute=0,second=0), end.replace(hour=23,minute=59,second=59), 'relative'))
            except (ValueError, TypeError):
                continue
    
    # 3. Check relative patterns (Russian)
    for pattern, ptype in RELATIVE_PATTERNS_RU:
        for match in re.finditer(pattern, text_lower):
            expr = match.group(0)
            found_expressions.append(expr)
            try:
                if ptype == 'relative_day':
                    start, end = resolve_relative_day(match.group(1), reference_date)
                    resolved_ranges.append((start, end, 'relative'))
                elif ptype == 'relative_ago':
                    amount = int(match.group(1))
                    unit = match.group(2)
                    start, end = resolve_relative_ago(amount, unit, reference_date)
                    resolved_ranges.append((start, end, 'relative'))
                elif ptype == 'month_ref':
                    month_str = match.group(1)
                    year = int(match.group(2)) if match.lastindex >= 2 and match.group(2) else None
                    start, end = resolve_month_ref(month_str, year, reference_date)
                    resolved_ranges.append((start, end, 'relative'))
            except (ValueError, TypeError):
                continue

    
    # 4. Select best range: prefer explicit > relative, then most specific
    if not resolved_ranges:
        return {
            "expressions": found_expressions if found_expressions else [],
            "t_event_start": None,
            "t_event_end": None
        }
    
    # Sort: explicit first, then by narrowest range
    resolved_ranges.sort(key=lambda r: (0 if r[2] == 'explicit' else 1, (r[1] - r[0]).total_seconds()))
    best = resolved_ranges[0]
    
    return {
        "expressions": found_expressions,
        "t_event_start": best[0].isoformat(),
        "t_event_end": best[1].isoformat()
    }


def compute_temporal_overlap(query_start: str, query_end: str, 
                              note_start: str, note_end: str) -> float:
    """
    Compute temporal overlap score between query range and note range.
    Returns 0.0 (no overlap) to 1.0 (perfect overlap).
    Used as δ signal in blend scoring.
    """
    try:
        qs = datetime.fromisoformat(query_start)
        qe = datetime.fromisoformat(query_end)
        ns = datetime.fromisoformat(note_start)
        ne = datetime.fromisoformat(note_end)
    except (ValueError, TypeError):
        return 0.0
    
    # Calculate overlap
    overlap_start = max(qs, ns)
    overlap_end = min(qe, ne)
    
    if overlap_start >= overlap_end:
        return 0.0  # No overlap
    
    overlap_duration = (overlap_end - overlap_start).total_seconds()
    query_duration = max((qe - qs).total_seconds(), 1)  # Avoid division by zero
    
    # Score: what fraction of the query range is covered
    return min(overlap_duration / query_duration, 1.0)
