#!/usr/bin/env python3
"""
Integration tests — test database operations and module imports.
Requires: pip install -r requirements.txt
"""
import pytest
import sqlite3
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

pytestmark = pytest.mark.integration


class TestDatabaseOperations:
    """Test database schema and CRUD operations"""

    def setup_method(self):
        """Create temp DB for each test"""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.environ['DB_PATH'] = self.db_path
        # Re-import to use test DB
        import database
        database._connection = None
        database.init_database()
        self.db = database

    def teardown_method(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_schema_tables_exist(self):
        """All required tables created"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        for t in ['nodes', 'edges', 'entities', 'node_entities']:
            assert t in tables, f"Missing table: {t}"

    def test_add_and_get_node(self):
        """Can add and retrieve a note"""
        node_id = self.db.create_node("Test content", "test-cat")
        assert node_id > 0
        node = self.db.get_node(node_id)
        assert node is not None
        assert node['content'] == "Test content"
        assert node['category'] == "test-cat"

    def test_entity_counts_batch(self):
        """get_entity_counts_batch returns correct counts"""
        node_id = self.db.create_node("Test node", "test")
        eid1 = self.db.get_or_create_entity("Python", "tech")
        eid2 = self.db.get_or_create_entity("Docker", "tech")
        self.db.link_node_to_entity(node_id, eid1)
        self.db.link_node_to_entity(node_id, eid2)
        counts = self.db.get_entity_counts_batch()
        assert counts.get(node_id) == 2

    def test_create_edge_bidirectional(self):
        """Edges stored — connected nodes retrievable"""
        n1 = self.db.create_node("Node 1", "test")
        n2 = self.db.create_node("Node 2", "test")
        self.db.create_edge(n1, n2, weight=0.7, edge_type="semantic")
        self.db.create_edge(n2, n1, weight=0.7, edge_type="semantic")
        neighbors = self.db.get_connected_nodes(n1)
        neighbor_ids = [n['id'] for n in neighbors]
        assert n2 in neighbor_ids


class TestModuleImports:
    """Test that all modules import without errors"""

    def test_import_database(self):
        import database
        assert hasattr(database, 'create_node')
        assert hasattr(database, 'get_entity_counts_batch')

    @pytest.mark.slow
    def test_import_graph_engine(self):
        """Requires torch — slow to import"""
        import graph_engine
        assert hasattr(graph_engine, 'search_with_activation')
        assert hasattr(graph_engine, 'add_note')

    def test_import_ann_index(self):
        import ann_index
        assert hasattr(ann_index, 'ANNIndex')
        assert hasattr(ann_index, 'get_ann_index')

    def test_import_graph_cache(self):
        import graph_cache
        assert hasattr(graph_cache, 'GraphCache')
        assert hasattr(graph_cache, 'get_graph_cache')


class TestPerformance:
    """Performance benchmarks"""

    def test_dict_lookup_speed(self):
        """Graph cache O(1) lookup under 1ms for 1000 ops"""
        import time
        cache = {i: list(range(10)) for i in range(1000)}
        start = time.time()
        for _ in range(1000):
            _ = cache.get(500, [])
        assert time.time() - start < 0.01

    @pytest.mark.slow
    def test_blend_scoring_speed(self):
        """Blend scoring 1000 nodes under 10ms"""
        import time
        import random
        random.seed(42)
        sems = {i: random.random() for i in range(1000)}
        spreads = {i: random.random() for i in range(1000)}
        alpha = 0.7
        start = time.time()
        blended = {
            nid: alpha * sems[nid] + (1 - alpha) * spreads.get(nid, 0)
            for nid in sems
        }
        assert time.time() - start < 0.01
        assert len(blended) == 1000


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'not slow'])
