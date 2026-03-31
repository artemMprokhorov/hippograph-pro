"""
Late Chunking for HippoGraph — Experiment D (March 2026)

Overlap chunking with standard dense encode.
No ColBERT, no GPU required. ~50ms per chunk.

Strategy:
- Split long notes into sentence-aware chunks
- 50% token overlap between chunks (context preservation)
- Each chunk encoded with standard model.encode()
- PART_OF edges link chunks to parent note
"""

import os
import re
import numpy as np
from typing import List, Dict

LC_ENABLED = os.environ.get('LATE_CHUNKING_ENABLED', 'false').lower() == 'true'
LC_CHUNK_CHARS = int(os.environ.get('LC_CHUNK_CHARS', '400'))   # chars per chunk
LC_OVERLAP_CHARS = int(os.environ.get('LC_OVERLAP_CHARS', '200'))  # overlap chars (~50%)
LC_MIN_NOTE_CHARS = int(os.environ.get('LC_MIN_NOTE_CHARS', '600'))  # min to chunk


def split_into_sentences(text: str) -> List[str]:
    """Split text at sentence boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def build_overlap_chunks(text: str, chunk_chars: int, overlap_chars: int) -> List[str]:
    """
    Build overlapping chunks from text, respecting sentence boundaries.
    Each chunk is ~chunk_chars long with ~overlap_chars overlap with next chunk.
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

            # Keep last N chars worth of sentences as overlap
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

    # Add remaining
    if current:
        remaining = ' '.join(current)
        # Only add if meaningfully different from last chunk
        if not chunks or remaining != chunks[-1]:
            chunks.append(remaining)

    return chunks


def late_chunk_encode(content: str, model) -> List[Dict]:
    """
    Overlap chunking with standard dense encode.

    Fast (~50ms per chunk), works on CPU, no ColBERT needed.
    Context preserved through sentence overlap between chunks.

    Returns list of {text, embedding, chunk_idx, total_chunks}
    or empty list if disabled / content too short.
    """
    if not LC_ENABLED:
        return []

    if len(content) < LC_MIN_NOTE_CHARS:
        return []

    try:
        chunk_texts = build_overlap_chunks(content, LC_CHUNK_CHARS, LC_OVERLAP_CHARS)

        if len(chunk_texts) < 2:
            return []  # No benefit from chunking

        # Encode all chunks in one batch call
        embeddings = model.encode(chunk_texts)

        chunks = []
        for i, (text, emb) in enumerate(zip(chunk_texts, embeddings)):
            # Normalize
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            chunks.append({
                'text': text,
                'embedding': emb.astype(np.float32),
                'chunk_idx': i,
                'total_chunks': len(chunk_texts),
            })

        print(f'📝 Overlap chunking: {len(chunks)} chunks for note ({len(content)} chars)')
        return chunks

    except Exception as e:
        print(f'late_chunk_encode error: {e}')
        return []