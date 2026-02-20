"""
Reranker — Cross-encoder reranking pass for top-N candidates.

Uses a lightweight cross-encoder to re-score (query, document) pairs
for improved precision after initial blend scoring.

Architecture:
    1. Initial retrieval: blend scoring returns top-N candidates (N=20-50)
    2. Reranking: cross-encoder scores each (query, candidate) pair
    3. Final: reranked scores blended with original scores

Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (~80MB)
    - Trained on MS MARCO passage ranking
    - Fast inference: ~5ms per pair on CPU
    - Good balance of speed vs quality

Usage:
    from reranker import get_reranker
    reranker = get_reranker()
    reranked = reranker.rerank(query, candidates, top_k=5)
"""

import os
import time

# Lazy singleton
_reranker_instance = None


def get_reranker():
    """Get or create singleton reranker instance."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = Reranker()
    return _reranker_instance


RERANK_ENABLED = os.environ.get("RERANK_ENABLED", "false").lower() == "true"
RERANK_MODEL = os.environ.get("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANK_TOP_N = int(os.environ.get("RERANK_TOP_N", "20"))  # rerank this many candidates
RERANK_WEIGHT = float(os.environ.get("RERANK_WEIGHT", "0.3"))  # blend weight for reranker score


class Reranker:
    """Cross-encoder reranker for improving retrieval precision."""

    def __init__(self):
        self._model = None
        self._is_loaded = False

    def _load_model(self):
        """Lazy-load cross-encoder model on first use."""
        if self._is_loaded:
            return
        try:
            from sentence_transformers import CrossEncoder
            start = time.time()
            self._model = CrossEncoder(RERANK_MODEL)
            elapsed = time.time() - start
            print(f"🎯 Reranker loaded: {RERANK_MODEL} in {elapsed:.2f}s")
            self._is_loaded = True
        except Exception as e:
            print(f"⚠️ Reranker failed to load: {e}")
            self._model = None
            self._is_loaded = True  # don't retry

    @property
    def is_available(self):
        """Check if reranker is enabled and model loaded."""
        if not RERANK_ENABLED:
            return False
        if not self._is_loaded:
            self._load_model()
        return self._model is not None

    def rerank(self, query: str, candidates: list, top_k: int = 5) -> list:
        """
        Rerank candidates using cross-encoder.

        Args:
            query: Search query string
            candidates: List of (node_id, blend_score, content) tuples
            top_k: Number of results to return after reranking

        Returns:
            List of (node_id, final_score) tuples, sorted by final score.
            final_score = (1 - RERANK_WEIGHT) × blend_score + RERANK_WEIGHT × rerank_score
        """
        if not self.is_available or not candidates:
            # Passthrough: return original scores
            return [(nid, score) for nid, score, _ in candidates[:top_k]]

        # Prepare pairs for cross-encoder
        pairs = [(query, content) for _, _, content in candidates]

        start = time.time()
        try:
            raw_scores = self._model.predict(pairs)
        except Exception as e:
            print(f"⚠️ Rerank prediction failed: {e}")
            return [(nid, score) for nid, score, _ in candidates[:top_k]]
        elapsed = time.time() - start

        # Normalize reranker scores to [0, 1]
        min_s = min(raw_scores)
        max_s = max(raw_scores)
        if max_s > min_s:
            rerank_normalized = [(s - min_s) / (max_s - min_s) for s in raw_scores]
        else:
            rerank_normalized = [0.5] * len(raw_scores)

        # Blend original scores with reranker scores
        w = RERANK_WEIGHT
        final = []
        for i, (node_id, blend_score, _) in enumerate(candidates):
            combined = (1 - w) * blend_score + w * rerank_normalized[i]
            final.append((node_id, combined))

        final.sort(key=lambda x: x[1], reverse=True)
        print(f"🎯 Reranked {len(candidates)} → top {top_k} in {elapsed*1000:.0f}ms")

        return final[:top_k]
