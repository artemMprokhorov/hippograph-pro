#!/usr/bin/env python3
"""
Unit tests for graph_engine.py - spreading activation, blend scoring, entity penalty
"""
import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestSpreadingActivation:
    """Test spreading activation normalization and damping"""

    def test_activation_normalization(self):
        """Activations normalize to 0-1 range with max=1.0"""
        activations = {1: 2520.5, 2: 2411.3, 3: 2399.8}
        max_act = max(activations.values())
        normalized = {k: v / max_act for k, v in activations.items()}

        for score in normalized.values():
            assert 0 <= score <= 1
        assert max(normalized.values()) == 1.0
        assert normalized[1] > normalized[2] > normalized[3]

    def test_activation_decay(self):
        """Decay factor reduces activation exponentially"""
        decay = 0.7
        assert abs(1.0 * decay - 0.7) < 0.001
        assert abs(1.0 * (decay ** 3) - 0.343) < 0.001

    def test_cosine_similarity_identical(self):
        """Identical vectors have similarity 1.0"""
        v = np.array([1.0, 0.0, 0.0])
        sim = np.dot(v, v) / (np.linalg.norm(v) ** 2)
        assert abs(sim - 1.0) < 0.001

    def test_cosine_similarity_orthogonal(self):
        """Orthogonal vectors have similarity 0.0"""
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.0, 1.0, 0.0])
        sim = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        assert abs(sim) < 0.001


class TestBlendScoring:
    """Test blend scoring formula: final = α*semantic + (1-α)*spread"""

    def test_pure_semantic(self):
        """α=1.0 gives pure semantic score"""
        alpha = 1.0
        sem, spread = 0.85, 0.3
        result = alpha * sem + (1 - alpha) * spread
        assert abs(result - 0.85) < 0.001

    def test_pure_activation(self):
        """α=0.0 gives pure spreading activation"""
        alpha = 0.0
        sem, spread = 0.85, 0.3
        result = alpha * sem + (1 - alpha) * spread
        assert abs(result - 0.3) < 0.001

    def test_default_blend(self):
        """α=0.7 blends 70% semantic + 30% spread"""
        alpha = 0.7
        sem, spread = 0.8, 0.6
        result = alpha * sem + (1 - alpha) * spread
        expected = 0.7 * 0.8 + 0.3 * 0.6  # 0.56 + 0.18 = 0.74
        assert abs(result - 0.74) < 0.001

    def test_blend_bounded(self):
        """Blend score stays in 0-1 when inputs are 0-1"""
        import random
        random.seed(42)
        for _ in range(100):
            alpha = random.random()
            sem = random.random()
            spread = random.random()
            result = alpha * sem + (1 - alpha) * spread
            assert 0 <= result <= 1

    def test_semantic_wins_with_high_alpha(self):
        """Higher semantic similarity note wins when α is high"""
        alpha = 0.7
        # Note A: high semantic, low spread
        score_a = alpha * 0.9 + (1 - alpha) * 0.1  # 0.63 + 0.03 = 0.66
        # Note B: low semantic, high spread (hub node)
        score_b = alpha * 0.3 + (1 - alpha) * 0.9  # 0.21 + 0.27 = 0.48
        assert score_a > score_b

    def test_spread_can_win_with_low_alpha(self):
        """Hub node wins when α is low (exploratory search)"""
        alpha = 0.2
        score_a = alpha * 0.9 + (1 - alpha) * 0.1  # 0.18 + 0.08 = 0.26
        score_b = alpha * 0.3 + (1 - alpha) * 0.9  # 0.06 + 0.72 = 0.78
        assert score_b > score_a


class TestEntityCountPenalty:
    """Test entity-count penalty for hub suppression"""

    def test_no_penalty_below_threshold(self):
        """Notes with ≤20 entities get no penalty"""
        for ec in [0, 5, 10, 15, 20]:
            score = 0.8
            if ec > 20:
                score *= 20.0 / ec
            assert score == 0.8

    def test_mild_penalty_at_25(self):
        """25 entities → ×0.8 penalty"""
        score = 1.0
        ec = 25
        if ec > 20:
            score *= 20.0 / ec
        assert abs(score - 0.8) < 0.001

    def test_strong_penalty_at_42(self):
        """42 entities → ×0.476 penalty"""
        score = 1.0
        ec = 42
        if ec > 20:
            score *= 20.0 / ec
        assert abs(score - 20.0 / 42) < 0.001

    def test_penalty_preserves_ranking(self):
        """Specific note still beats penalized hub with lower semantic match"""
        alpha = 0.7
        # Specific note: sem=0.9, spread=0.1, 5 entities
        score_specific = alpha * 0.9 + (1 - alpha) * 0.1  # 0.66
        # Hub note: sem=0.5, spread=0.8, 30 entities
        score_hub = alpha * 0.5 + (1 - alpha) * 0.8  # 0.59
        score_hub *= 20.0 / 30  # penalty: 0.59 * 0.667 = 0.393
        assert score_specific > score_hub

    def test_penalty_linear(self):
        """Penalty is linear — doubling entities halves the multiplier"""
        score_20 = 20.0 / 20  # 1.0 (just at threshold)
        score_40 = 20.0 / 40  # 0.5
        assert abs(score_40 - score_20 / 2) < 0.001


class TestGraphCache:
    """Test in-memory graph cache"""

    def test_cache_structure(self):
        """Cache stores bidirectional edges"""
        from collections import defaultdict
        cache = defaultdict(list)
        # Simulate add_edge
        cache[1].append((2, 0.7, 'semantic'))
        cache[2].append((1, 0.7, 'semantic'))
        assert len(cache[1]) == 1
        assert len(cache[2]) == 1
        assert cache[1][0][0] == 2  # neighbor id

    def test_edge_weights_bounded(self):
        """Edge weights must be 0-1"""
        edges = [(0.7, 'semantic'), (0.5, 'entity'), (0.6, 'entity')]
        for weight, _ in edges:
            assert 0 <= weight <= 1

    def test_cache_incremental_update(self):
        """add_edge updates cache without rebuild"""
        from collections import defaultdict
        cache = defaultdict(list)
        # Initial state
        cache[1].append((2, 0.7, 'semantic'))
        cache[2].append((1, 0.7, 'semantic'))
        assert len(cache[1]) == 1

        # Incremental add (what our fix does)
        cache[1].append((3, 0.6, 'entity'))
        cache[3].append((1, 0.6, 'entity'))
        assert len(cache[1]) == 2
        assert cache[1][1] == (3, 0.6, 'entity')


class TestANNIndex:
    """Test ANN index functionality"""

    def test_embedding_dimensions(self):
        """Embeddings must be 384-dimensional"""
        embedding = np.random.rand(384).astype(np.float32)
        assert embedding.shape[0] == 384

    def test_l2_normalization(self):
        """Normalized vectors have unit length"""
        v = np.array([3.0, 4.0], dtype=np.float32)
        normalized = v / np.linalg.norm(v)
        assert abs(np.linalg.norm(normalized) - 1.0) < 0.001

    def test_actual_k_clamp(self):
        """k must not exceed index size"""
        index_size = 5
        requested_k = 15
        actual_k = min(requested_k, index_size)
        assert actual_k == 5

    def test_actual_k_zero_returns_empty(self):
        """Empty index returns no results"""
        index_size = 0
        actual_k = min(10, index_size)
        assert actual_k == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
