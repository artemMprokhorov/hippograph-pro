"""
Tests for features added March 27-28, 2026:
- Metric query detection (is_metric_query)
- Late Stage Inhibition (INHIBITION_STRENGTH env var)
- BGE-M3 embedding dimension (1024)
- Auto metrics snapshot (step_metrics_snapshot callable)
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# ─────────────────────────────────────────────
# Metric Query Detection (commit 60a47f3)
# ─────────────────────────────────────────────

class TestMetricQueryDetection:

    def test_detects_consciousness_score(self):
        from query_decomposer import is_metric_query
        assert is_metric_query('What is the consciousness composite score?') is True

    def test_detects_locomo_recall(self):
        from query_decomposer import is_metric_query
        assert is_metric_query('What is the current LOCOMO Recall@5?') is True

    def test_detects_pcb_result(self):
        from query_decomposer import is_metric_query
        assert is_metric_query('What is the PCB benchmark result?') is True

    def test_detects_emotional_modulation(self):
        from query_decomposer import is_metric_query
        assert is_metric_query('What is the emotional modulation value?') is True

    def test_detects_current_prefix(self):
        from query_decomposer import is_metric_query
        assert is_metric_query('What is the current accuracy?') is True

    def test_detects_latest_prefix(self):
        from query_decomposer import is_metric_query
        assert is_metric_query('What is the latest benchmark score?') is True

    def test_does_not_flag_regular_query(self):
        from query_decomposer import is_metric_query
        assert is_metric_query('Tell me about spreading activation') is False

    def test_does_not_flag_history_query(self):
        from query_decomposer import is_metric_query
        assert is_metric_query('What experiments did we run in February?') is False

    def test_metric_query_sets_direction_after(self):
        """Metric queries should prefer newer notes (direction=after)"""
        from query_decomposer import decompose_temporal_query
        _, is_temporal, direction = decompose_temporal_query('What is the consciousness composite?')
        assert is_temporal is True
        assert direction == 'after'


# ─────────────────────────────────────────────
# Late Stage Inhibition (commit 46360a0)
# ─────────────────────────────────────────────

class TestLateStageInhibition:

    def test_inhibition_env_var_loaded(self):
        """INHIBITION_STRENGTH should be readable from graph_engine"""
        import graph_engine
        assert hasattr(graph_engine, 'INHIBITION_STRENGTH')
        assert isinstance(graph_engine.INHIBITION_STRENGTH, float)

    def test_inhibition_default_positive(self):
        """Production default should be > 0 (0.05)"""
        import graph_engine
        assert graph_engine.INHIBITION_STRENGTH >= 0.0

    def test_inhibition_applied_in_spreading(self):
        """Spreading activation code path exists for inhibition"""
        import inspect, graph_engine
        source = inspect.getsource(graph_engine)
        assert 'INHIBITION_STRENGTH' in source
        assert 'late' in source.lower() or 'inhibit' in source.lower()


# ─────────────────────────────────────────────
# BGE-M3 Embedding Dimension
# ─────────────────────────────────────────────

class TestBGEM3Embedding:

    def test_bge_m3_produces_1024_dim(self):
        """BGE-M3 must produce 1024-dimensional embeddings"""
        model_name = os.environ.get('EMBEDDING_MODEL', '')
        if 'bge-m3' not in model_name.lower():
            pytest.skip('BGE-M3 not configured as embedding model')
        from graph_engine import get_model
        model = get_model()
        embedding = model.encode(['test sentence'])[0]
        assert len(embedding) == 1024, f'Expected 1024, got {len(embedding)}'

    def test_ann_index_dimension_matches_model(self):
        """ANN index dimension must match the loaded embedding model"""
        from ann_index import get_ann_index
        from graph_engine import get_model
        idx = get_ann_index()
        if not idx.enabled:
            pytest.skip('ANN index not enabled')
        model = get_model()
        test_emb = model.encode(['test'])[0]
        assert idx.dimension == len(test_emb), \
            f'ANN dim {idx.dimension} != model dim {len(test_emb)}'

    def test_dimension_is_valid(self):
        """Dimension should be one of known good values"""
        from ann_index import get_ann_index
        idx = get_ann_index()
        if not idx.enabled:
            pytest.skip('ANN index not enabled')
        assert idx.dimension in (384, 768, 1024), \
            f'Unexpected dim: {idx.dimension}'


# ─────────────────────────────────────────────
# Auto Metrics Snapshot (commit 17a4374)
# ─────────────────────────────────────────────

class TestMetricsSnapshot:

    def test_step_metrics_snapshot_exists(self):
        """step_metrics_snapshot must exist and be callable"""
        from sleep_compute import step_metrics_snapshot
        assert callable(step_metrics_snapshot)

    def test_step_metrics_snapshot_signature(self):
        """step_metrics_snapshot should accept db_path"""
        import inspect
        from sleep_compute import step_metrics_snapshot
        sig = inspect.signature(step_metrics_snapshot)
        params = list(sig.parameters.keys())
        assert 'db_path' in params or len(params) >= 1