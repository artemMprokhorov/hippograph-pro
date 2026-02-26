#!/usr/bin/env python3
"""
GLiNER2 Relation Extractor for HippoGraph Pro
Zero-shot relation extraction using GLiNER2 unified framework.
Model: fastino/gliner2-large-v1 (~205M params, CPU-optimized, Apache 2.0)

Used in sleep_compute.py (Deep Sleep phase) to build typed edges between
entity nodes in the knowledge graph.
"""
import os
from typing import List, Tuple, Optional

GLINER2_MODEL = os.getenv("GLINER2_MODEL", "fastino/gliner2-large-v1")
GLINER2_THRESHOLD = float(os.getenv("GLINER2_THRESHOLD", "0.3"))

# Relation types for HippoGraph knowledge graph
# Designed to work with our entity taxonomy:
# person, organization, location, tech, concept, product, project, temporal, event
GLINER2_RELATIONS = [
    "works_for",       # person -> organization
    "part_of",         # entity -> larger entity/project
    "uses",            # project/person -> technology/tool
    "created_by",      # product/concept -> person/organization
    "related_to",      # generic semantic relation
    "located_in",      # entity -> location
    "depends_on",      # tech/project -> tech/project
    "implements",      # project -> concept/standard
    "successor_of",    # v2 -> v1, new -> old
    "collaborates_with",  # person/org -> person/org
]

# Singleton model instance
_model = None
_available = None


def _load_model():
    """Load GLiNER2 model (cached singleton)."""
    global _model
    if _model is None:
        try:
            from gliner2 import GLiNER2
            _model = GLiNER2.from_pretrained(GLINER2_MODEL)
            print(f"✅ GLiNER2 loaded: {GLINER2_MODEL}")
        except ImportError:
            print("⚠️ gliner2 package not installed. Run: pip install gliner2")
            _model = False
        except Exception as e:
            print(f"⚠️ GLiNER2 load failed: {e}")
            _model = False
    return _model if _model is not False else None


def is_available() -> bool:
    """Check if GLiNER2 is available."""
    global _available
    if _available is None:
        try:
            model = _load_model()
            _available = model is not None
        except Exception:
            _available = False
    return _available


def reset_availability():
    """Reset availability cache (e.g. after install)."""
    global _available, _model
    _available = None
    _model = None


def extract_relations(
    text: str,
    relations: Optional[List[str]] = None,
    threshold: Optional[float] = None
) -> List[Tuple[str, str, str]]:
    """
    Extract typed relations from text.

    Returns: List of (subject, relation_type, object) triples.
    Example: [("Claude", "works_for", "Anthropic"), ("HippoGraph", "uses", "FAISS")]
    """
    model = _load_model()
    if model is None:
        return []

    if relations is None:
        relations = GLINER2_RELATIONS
    if threshold is None:
        threshold = GLINER2_THRESHOLD

    try:
        raw = model.extract_relations(text, relations)
        # GLiNER2 wraps output: {'relation_extraction': {'works_for': [...], ...}}
        result = raw.get("relation_extraction", raw)
        triples = []
        seen = set()

        for rel_type, pairs in result.items():
            if not isinstance(pairs, list):
                continue
            for pair in pairs:
                # GLiNER2 returns dicts with 'head', 'tail', optionally 'score'
                if isinstance(pair, dict):
                    head = pair.get("head", "").strip()
                    tail = pair.get("tail", "").strip()
                    score = pair.get("score", 1.0)
                elif isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    head, tail = str(pair[0]).strip(), str(pair[1]).strip()
                    score = pair[2] if len(pair) > 2 else 1.0
                else:
                    continue

                if not head or not tail or len(head) < 2 or len(tail) < 2:
                    continue
                if float(score) < threshold:
                    continue

                key = (head.lower(), rel_type, tail.lower())
                if key not in seen:
                    seen.add(key)
                    triples.append((head, rel_type, tail))

        return triples

    except Exception as e:
        print(f"⚠️ GLiNER2 relation extraction failed: {e}")
        return []


def extract_relations_batch(
    texts: List[str],
    relations: Optional[List[str]] = None,
    threshold: Optional[float] = None,
    batch_size: int = 8
) -> List[List[Tuple[str, str, str]]]:
    """
    Batch relation extraction for multiple texts.
    Returns one list of triples per input text.
    """
    model = _load_model()
    if model is None:
        return [[] for _ in texts]

    if relations is None:
        relations = GLINER2_RELATIONS
    if threshold is None:
        threshold = GLINER2_THRESHOLD

    try:
        batch_results = model.batch_extract_relations(
            texts, relations, batch_size=batch_size
        )
        output = []
        for raw in batch_results:
            # GLiNER2 wraps: {'relation_extraction': {'rel_type': [...], ...}}
            result = raw.get("relation_extraction", raw)
            triples = []
            seen = set()
            for rel_type, pairs in result.items():
                if not isinstance(pairs, list):
                    continue
                for pair in pairs:
                    if isinstance(pair, dict):
                        head = pair.get("head", "").strip()
                        tail = pair.get("tail", "").strip()
                        score = pair.get("score", 1.0)
                    elif isinstance(pair, (list, tuple)) and len(pair) >= 2:
                        head, tail = str(pair[0]).strip(), str(pair[1]).strip()
                        score = pair[2] if len(pair) > 2 else 1.0
                    else:
                        continue

                    if not head or not tail or len(head) < 2 or len(tail) < 2:
                        continue
                    if float(score) < threshold:
                        continue

                    key = (head.lower(), rel_type, tail.lower())
                    if key not in seen:
                        seen.add(key)
                        triples.append((head, rel_type, tail))
            output.append(triples)
        return output

    except Exception as e:
        print(f"⚠️ GLiNER2 batch extraction failed: {e}")
        return [[] for _ in texts]
