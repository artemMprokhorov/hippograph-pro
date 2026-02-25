#!/usr/bin/env python3
"""
GLiNER Entity Extractor for HippoGraph Pro
Zero-shot NER using bidirectional transformer — quality of LLM, speed of spaCy.
Model: urchade/gliner_multi-v2.1 (~600MB, CPU-optimized)
"""
import os
from typing import List, Tuple, Optional

# Configurable model
GLINER_MODEL = os.getenv("GLINER_MODEL", "urchade/gliner_multi-v2.1")
GLINER_THRESHOLD = float(os.getenv("GLINER_THRESHOLD", "0.4"))

# Entity types matching HippoGraph taxonomy
GLINER_LABELS = [
    "person", "organization", "location", "technology",
    "concept", "product", "project", "temporal", "event"
]

# Singleton model instance
_model = None
_available = None


def _load_model():
    """Load GLiNER model (cached singleton)."""
    global _model
    if _model is None:
        try:
            from gliner import GLiNER
            _model = GLiNER.from_pretrained(GLINER_MODEL)
            print(f"✅ GLiNER loaded: {GLINER_MODEL}")
        except Exception as e:
            print(f"⚠️ GLiNER load failed: {e}")
            _model = False  # Mark as failed, don't retry
    return _model if _model is not False else None


def is_available() -> bool:
    """Check if GLiNER is available."""
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


def extract_entities_gliner(text: str,
                            labels: Optional[List[str]] = None,
                            threshold: Optional[float] = None
                            ) -> List[Tuple[str, str]]:
    """
    Extract entities using GLiNER zero-shot NER.
    Returns: List of (entity_text, entity_type) tuples.
    """
    model = _load_model()
    if model is None:
        return []

    if labels is None:
        labels = GLINER_LABELS
    if threshold is None:
        threshold = GLINER_THRESHOLD

    try:
        predictions = model.predict_entities(text, labels, threshold=threshold)

        # Deduplicate and normalize
        seen = set()
        entities = []
        for pred in predictions:
            name = pred["text"].strip()
            etype = pred["label"]

            # Map "technology" -> "tech" for consistency with HippoGraph
            if etype == "technology":
                etype = "tech"

            # Skip noise
            if len(name) < 2:
                continue
            key = name.lower()
            if key not in seen:
                seen.add(key)
                entities.append((name, etype))

        return entities
    except Exception as e:
        print(f"⚠️ GLiNER extraction failed: {e}")
        return []


def extract_entities_gliner_with_confidence(
        text: str,
        labels: Optional[List[str]] = None,
        threshold: Optional[float] = None
) -> List[Tuple[str, str, float]]:
    """
    Extract entities with confidence scores.
    Returns: List of (entity_text, entity_type, confidence) tuples.
    """
    model = _load_model()
    if model is None:
        return []

    if labels is None:
        labels = GLINER_LABELS
    if threshold is None:
        threshold = GLINER_THRESHOLD

    try:
        predictions = model.predict_entities(text, labels, threshold=threshold)

        seen = set()
        entities = []
        for pred in predictions:
            name = pred["text"].strip()
            etype = pred["label"]
            score = pred.get("score", 0.8)

            if etype == "technology":
                etype = "tech"
            if len(name) < 2:
                continue
            key = name.lower()
            if key not in seen:
                seen.add(key)
                entities.append((name, etype, score))

        return entities
    except Exception as e:
        print(f"⚠️ GLiNER extraction failed: {e}")
        return []
