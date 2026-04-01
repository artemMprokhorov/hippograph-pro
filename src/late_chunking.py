"""
Late Chunking for HippoGraph

LC_MODE=parent         -- D1 production, PART_OF edges
LC_MODE=parentless     -- E1, no parent
LC_MODE=uroboros       -- E2, circular NEXT_CHUNK
LC_MODE=uroboros_semantic -- E3, semantic ring
"""

import os
import re
import numpy as np
from typing import List, Dict

LC_ENABLED = os.environ.get('LATE_CHUNKING_ENABLED', 'false').lower() == 'true'
LC_MODE    = os.environ.get('LC_MODE', 'parent')
LC_CHUNK_CHARS    = int(os.environ.get('LC_CHUNK_CHARS', '400'))
LC_OVERLAP_CHARS  = int(os.environ.get('LC_OVERLAP_CHARS', '200'))
LC_MIN_NOTE_CHARS = int(os.environ.get('LC_MIN_NOTE_CHARS', '300'))

LC_PARENTLESS        = LC_MODE == 'parentless'
LC_UROBOROS          = LC_MODE == 'uroboros'
LC_UROBOROS_SEMANTIC = LC_MODE == 'uroboros_semantic'


PH_ELL = chr(0x00B6) + 'ELL' + chr(0x00B6)
PH_DEC = chr(0x00B6) + 'DEC' + chr(0x00B6)
PH_LST = chr(0x00B6) + 'LST' + chr(0x00B6)
PH_ABV = chr(0x00B6) + 'ABV' + chr(0x00B6)
_ABBREVS = {
    # English
    'dr', 'mr', 'mrs', 'ms', 'prof', 'sr', 'jr', 'vs', 'etc', 'e.g', 'i.e',
    'fig', 'eq', 'vol', 'no', 'pp', 'ed', 'est', 'approx', 'dept', 'corp', 'inc', 'ltd', 'co',
    'v', 'ver', 'rev', 'ref', 'sec', 'st', 'ave', 'blvd',
    # Russian
    'т', 'к', 'м', 'г', 'л', 'см', 'мм', 'км', 'мг', 'мл', 'тыс', 'млн',
    'др', 'проф', 'г-н', 'стр', 'им', 'тд', 'те', 'век', 'обл', 'гор', 'район',
    # Spanish
    'sra', 'srta', 'dra', 'lic', 'ing', 'arq',
    # German
    'str', 'hr', 'fr', 'abb', 'z.b', 'u.a', 'd.h', 'bzw', 'ca',
    # French
    'mme', 'mlle', 'av', 'bd', 'p.ex',
    # Italian
    'sig', 'dott',
}


def _protect(text: str) -> str:
    """Защищаем ложные точки через Unicode placeholderы."""
    # 1. Эллипсис
    text = text.replace('...', PH_ELL)
    # 2. Десятичные числа (сначала!): 91.1  0.830  78.7
    text = re.sub(r'(\d)\.(\d)', lambda m: m.group(1) + PH_DEC + m.group(2), text)
    # 3. Нумерованные списки: 1. 2. 10. — но не если перед ними стоит DEC placeholder
    text = re.sub(r'(?<![\w\xb6])(\d{1,3})\.(?=\s)', lambda m: m.group(1) + PH_LST, text)
    # 4. Идентификаторы с дефисом — НЕ защищаем, это обычный конец предложения
    # 5. Аббревиатуры (Dr. Mr. etc.)
    def _repl_abbrev(m):
        w = m.group(1).lower()
        if w in _ABBREVS:
            return m.group(1) + PH_ABV
        return m.group(0)
    text = re.sub(r'\b([A-Za-z\u0410-\u044f\u0451\u0401]{1,6})\.(?=\s)', _repl_abbrev, text)
    # 6. Инициалы: " A. "
    text = re.sub(r'(?<=\s)([A-Z\u0410-\u042f\u0401])\.(?=\s)', lambda m: m.group(1) + PH_ABV, text)
    # 7. Версии: E1. D1. v2.
    # (rule 7 removed: letter+digit before dot causes false positives on v2, m3)
    return text


def _restore(text: str) -> str:
    text = text.replace(PH_ELL, '...')
    text = text.replace(PH_DEC, '.')
    text = text.replace(PH_LST, '.')
    text = text.replace(PH_ABV, '.')
    return text


def split_into_sentences(text: str) -> List[str]:
    """
    Split text at real sentence boundaries.
    Protects: decimals (91.1), lists (1. 2.), abbrevs (Dr.), hyphens, versions.
    """
    protected = _protect(text)
    # Теперь все ложные точки заменены — разбиваем по [.!?]+\s+
    parts = re.split(r'(?<=[.!?])\s+', protected)
    sentences = [_restore(p.strip()) for p in parts if p.strip()]
    return sentences


def build_overlap_chunks(text: str, chunk_chars: int, overlap_chars: int,
                         circular: bool = False) -> List[str]:
    """
    Build overlapping chunks from text, respecting sentence boundaries.
    """
    sentences = split_into_sentences(text)
    if not sentences:
        return []

    chunks = []
    current = []
    current_len = 0

    for sent in sentences:
        current.append(sent)
        current_len += len(sent) + 1

        if current_len >= chunk_chars:
            chunk_text = ' '.join(current)
            chunks.append(chunk_text)

            overlap = []
            overlap_len = 0
            for s in reversed(current):
                if overlap_len + len(s) <= overlap_chars:
                    overlap.insert(0, s)
                    overlap_len += len(s) + 1
                else:
                    break
            current = overlap
            current_len = overlap_len

    if current:
        remaining = ' '.join(current)
        if not chunks or remaining != chunks[-1]:
            if circular and chunks:
                head = text[:overlap_chars]
                remaining = remaining + ' ' + head
            chunks.append(remaining)
    elif circular and chunks:
        head = text[:overlap_chars]
        chunks[-1] = chunks[-1] + ' ' + head

    return chunks


def late_chunk_encode(content: str, model) -> List[Dict]:
    """Overlap chunking with standard dense encode."""
    if not LC_ENABLED:
        return []
    if len(content) < LC_MIN_NOTE_CHARS:
        return []
    try:
        circular_text = LC_UROBOROS_SEMANTIC
        chunk_texts = build_overlap_chunks(
            content, LC_CHUNK_CHARS, LC_OVERLAP_CHARS, circular=circular_text
        )
        if len(chunk_texts) < 2:
            return []
        embeddings = model.encode(chunk_texts)
        chunks = []
        for i, (text, emb) in enumerate(zip(chunk_texts, embeddings)):
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            chunks.append({
                'text': text,
                'embedding': emb.astype(np.float32),
                'chunk_idx': i,
                'total_chunks': len(chunk_texts),
            })
        print(f'[LC/{LC_MODE}] {len(chunks)} chunks ({len(content)} chars)')
        return chunks
    except Exception as e:
        print(f'late_chunk_encode error: {e}')
        return []