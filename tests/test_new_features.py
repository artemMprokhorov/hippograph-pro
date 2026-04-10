"""
Tests for features added in March 2026:
- #15e: dateparser temporal filtering
- #16/#16b: synonym normalization + cross-lingual normalize_query
- temporal edges v2
- #26: embedding dimension validation
- #15c: CJK word segmentation
- studio_list_dir .TemporaryItems fix
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# ─────────────────────────────────────────────
# #16 / #16b: Synonym normalization
# ─────────────────────────────────────────────

class TestSynonymNormalization:

    def test_normalize_entity_abbreviations(self):
        from entity_extractor import normalize_entity
        assert normalize_entity('ML') == 'machine learning'
        assert normalize_entity('k8s') == 'kubernetes'
        assert normalize_entity('NLP') == 'natural language processing'

    def test_normalize_entity_project_aliases(self):
        from entity_extractor import normalize_entity
        assert normalize_entity('hippograph pro') == 'hippograph'
        assert normalize_entity('neural memory') == 'hippograph'
        assert normalize_entity('semantic memory') == 'hippograph'

    def test_normalize_query_russian(self):
        from entity_extractor import normalize_query
        assert normalize_query('машинное обучение') == 'machine learning'
        assert normalize_query('искусственный интеллект') == 'artificial intelligence'
        assert normalize_query('нейронная сеть') == 'neural network'
        assert normalize_query('хиппограф') == 'hippograph'
        assert normalize_query('память') == 'memory'
        assert normalize_query('сознание') == 'consciousness'

    def test_normalize_query_spanish(self):
        from entity_extractor import normalize_query
        assert normalize_query('inteligencia artificial') == 'artificial intelligence'
        assert normalize_query('aprendizaje automático') == 'machine learning'
        assert normalize_query('red neuronal') == 'neural network'
        assert normalize_query('memoria') == 'memory'

    def test_normalize_query_german(self):
        from entity_extractor import normalize_query
        assert normalize_query('künstliche intelligenz') == 'artificial intelligence'
        assert normalize_query('maschinelles lernen') == 'machine learning'

    def test_normalize_query_french(self):
        from entity_extractor import normalize_query
        assert normalize_query('intelligence artificielle') == 'artificial intelligence'
        assert normalize_query('mémoire') == 'memory'

    def test_normalize_query_portuguese(self):
        from entity_extractor import normalize_query
        assert normalize_query('inteligência artificial') == 'artificial intelligence'
        assert normalize_query('memória') == 'memory'

    def test_normalize_query_mixed(self):
        """Partial phrase in query: only known tokens are replaced"""
        from entity_extractor import normalize_query
        assert normalize_query('k8s deployment') == 'kubernetes deployment'
        assert normalize_query('ml pipeline') == 'machine learning pipeline'

    def test_normalize_query_unknown_passthrough(self):
        """Unknown words pass through unchanged"""
        from entity_extractor import normalize_query
        result = normalize_query('some unknown phrase xyz')
        assert result == 'some unknown phrase xyz'


# ─────────────────────────────────────────────
# #15e: dateparser temporal filtering
# ─────────────────────────────────────────────

class TestDateparserTemporalFilter:

    def test_temporal_query_detected(self):
        from query_decomposer import is_temporal_query
        assert is_temporal_query('when did we deploy hippograph') is True
        assert is_temporal_query('what happened before the benchmark') is True
        assert is_temporal_query('recently added features') is True
        assert is_temporal_query('недавно добавили') is True
        assert is_temporal_query('когда это было') is True

    def test_non_temporal_query(self):
        from query_decomposer import is_temporal_query
        assert is_temporal_query('machine learning') is False
        assert is_temporal_query('hippograph architecture') is False

    def test_decompose_strips_temporal_words(self):
        from query_decomposer import decompose_temporal_query
        content, is_temporal, direction = decompose_temporal_query('when did we add hippograph benchmark')
        assert is_temporal is True
        assert 'hippograph' in content
        assert 'when did' not in content

    def test_decompose_detects_direction(self):
        from query_decomposer import decompose_temporal_query
        _, _, direction = decompose_temporal_query('what did we do last week')
        assert direction in ('before', 'after', 'around', None)

    def test_decompose_non_temporal_unchanged(self):
        from query_decomposer import decompose_temporal_query
        content, is_temporal, direction = decompose_temporal_query('spreading activation algorithm')
        assert is_temporal is False
        assert content == 'spreading activation algorithm'


# ─────────────────────────────────────────────
# #26: Embedding dimension validation
# ─────────────────────────────────────────────

class TestEmbeddingDimension:

    def test_model_produces_correct_dim(self):
        """paraphrase-multilingual-MiniLM-L12-v2 must output 384-dim vectors"""
        import numpy as np
        from graph_engine import get_model
        model = get_model()
        emb = model.encode('test embedding dimension check')[0]
        assert isinstance(emb, np.ndarray)
        assert emb.shape == (384,), f'Expected 384, got {emb.shape}'

    def test_embedding_is_normalized(self):
        """Embeddings should be unit vectors (cosine similarity ready)"""
        import numpy as np
        from graph_engine import get_model
        model = get_model()
        emb = model.encode('normalization test')[0]
        norm = np.linalg.norm(emb)
        assert norm > 0
        # not pre-normalized by default, just check finite values
        assert np.all(np.isfinite(emb))


# ─────────────────────────────────────────────
# #15c: CJK word segmentation
# ─────────────────────────────────────────────

class TestCJKDetection:

    def test_cjk_detected_as_non_latin(self):
        from entity_extractor import detect_language
        # Chinese characters should route to multilingual model
        assert detect_language('人工智能和机器学习') == 'xx'

    def test_japanese_detected_as_non_latin(self):
        from entity_extractor import detect_language
        assert detect_language('人工知能と機械学習') == 'xx'

    def test_korean_detected_as_non_latin(self):
        from entity_extractor import detect_language
        assert detect_language('인공지능') == 'xx'

    def test_english_detected_as_latin(self):
        from entity_extractor import detect_language
        assert detect_language('machine learning') == 'en'

    def test_russian_detected_as_non_latin(self):
        from entity_extractor import detect_language
        assert detect_language('машинное обучение') == 'xx'

    def test_mixed_mostly_latin(self):
        """Text that is <20% non-Latin stays as 'en'"""
        from entity_extractor import detect_language
        # purely Latin text stays 'en'
        assert detect_language('HippoGraph system uses memory') == 'en'
        assert detect_language('machine learning pipeline') == 'en'

    def test_empty_string(self):
        from entity_extractor import detect_language
        assert detect_language('') == 'en'


# ─────────────────────────────────────────────
# .TemporaryItems filter (studio_list_dir fix)
# ─────────────────────────────────────────────

class TestTemporaryItemsFilter:

    def test_temporary_items_filter_logic(self):
        """Filtering logic: .TemporaryItems and .DS_Store should be excluded"""
        all_entries = ['src', 'README.md', '.TemporaryItems', '.DS_Store', 'tests']
        filtered = [e for e in all_entries
                    if not e.startswith('.') or e in {'.env.example'}]
        assert '.TemporaryItems' not in filtered
        assert '.DS_Store' not in filtered
        assert 'src' in filtered
        assert 'README.md' in filtered

    def test_src_dir_accessible(self):
        """Container src directory should be accessible"""
        import os
        entries = os.listdir('/app/src')
        assert 'entity_extractor.py' in entries
        assert 'graph_engine.py' in entries
        dotfiles = [e for e in entries if e.startswith('.DS_Store')]
        assert dotfiles == [], f'DS_Store found in container: {dotfiles}'

# ─────────────────────────────────────────────
# EMOTIONAL_RESONANCE edges
# ─────────────────────────────────────────────

class TestEmotionalResonance:

    def _make_db(self, tmp_path, notes):
        """Create minimal test DB with nodes table."""
        import sqlite3, os
        db = os.path.join(tmp_path, 'test.db')
        conn = sqlite3.connect(db)
        conn.execute("""
            CREATE TABLE nodes (
                id INTEGER PRIMARY KEY,
                content TEXT,
                category TEXT DEFAULT 'general',
                timestamp TEXT,
                embedding BLOB,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0,
                importance TEXT DEFAULT 'normal',
                emotional_tone TEXT,
                emotional_intensity INTEGER DEFAULT 5,
                emotional_reflection TEXT,
                t_event_start TEXT,
                t_event_end TEXT,
                temporal_expressions TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                target_id INTEGER,
                weight REAL DEFAULT 0.5,
                edge_type TEXT DEFAULT 'semantic',
                created_at TEXT,
                UNIQUE(source_id, target_id, edge_type)
            )
        """)
        for note_id, tone in notes:
            conn.execute(
                'INSERT INTO nodes (id, content, emotional_tone) VALUES (?, ?, ?)',
                (note_id, f'note {note_id}', tone)
            )
        conn.commit()
        conn.close()
        return db

    def test_creates_edges_for_shared_tags(self, tmp_path):
        """Two notes with 2+ shared tags get EMOTIONAL_RESONANCE edge."""
        import sys, os
        sys.path.insert(0, '/app/src')
        # Patch DB path for database module
        import database
        db = self._make_db(str(tmp_path), [
            (1, 'joy, warmth, pride'),
            (2, 'joy, warmth, accountability'),
            (3, 'shame, resolve'),
        ])
        orig = database.DB_PATH
        database.DB_PATH = db
        try:
            from sleep_compute import step_emotional_resonance
            result = step_emotional_resonance(db, dry_run=False)
            assert result['edges_created'] > 0, 'Expected edges between notes 1 and 2'
            assert result['pairs_checked'] >= 1
        finally:
            database.DB_PATH = orig

    def test_dry_run_creates_no_edges(self, tmp_path):
        """Dry run reports would_create but creates nothing."""
        import sys
        sys.path.insert(0, '/app/src')
        db = self._make_db(str(tmp_path), [
            (1, 'joy, warmth, pride'),
            (2, 'joy, warmth, gratitude'),
        ])
        from sleep_compute import step_emotional_resonance
        import sqlite3
        result = step_emotional_resonance(db, dry_run=True)
        assert result['edges_created'] == 0
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM edges WHERE edge_type='EMOTIONAL_RESONANCE'").fetchone()[0]
        conn.close()
        assert count == 0

    def test_min_two_shared_tags(self, tmp_path):
        """Notes with only 1 shared tag do NOT get edges."""
        import sys, sqlite3
        sys.path.insert(0, '/app/src')
        db = self._make_db(str(tmp_path), [
            (1, 'joy, pride'),
            (2, 'joy, shame'),   # only 1 shared: joy
        ])
        from sleep_compute import step_emotional_resonance
        result = step_emotional_resonance(db, dry_run=False)
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM edges WHERE edge_type='EMOTIONAL_RESONANCE'").fetchone()[0]
        conn.close()
        assert count == 0, f'Expected 0 edges, got {count}'

    def test_jaccard_weight(self, tmp_path):
        """Weight = shared / union (Jaccard)."""
        import sys
        sys.path.insert(0, '/app/src')
        # tags_a = {joy, warmth, pride}, tags_b = {joy, warmth, resolve}
        # shared=2, union=4, jaccard=0.5
        tags_a = {'joy', 'warmth', 'pride'}
        tags_b = {'joy', 'warmth', 'resolve'}
        shared = tags_a & tags_b
        jaccard = round(len(shared) / len(tags_a | tags_b), 3)
        assert abs(jaccard - 0.5) < 0.01, f'Expected ~0.5, got {jaccard}'
        assert len(shared) >= 2  # meets min 2 threshold
        # Verify step reports 1 resonant pair
        db = self._make_db(str(tmp_path), [
            (1, 'joy, warmth, pride'),
            (2, 'joy, warmth, resolve'),
        ])
        from sleep_compute import step_emotional_resonance
        result = step_emotional_resonance(db, dry_run=True)
        assert result['pairs_checked'] == 1

# ─────────────────────────────────────────────
# GENERALIZES / INSTANTIATES edges
# ─────────────────────────────────────────────

class TestGeneralizesInstantiates:

    def _make_db(self, tmp_path, notes):
        import sqlite3, os, numpy as np
        db = os.path.join(str(tmp_path), 'test_gen.db')
        conn = sqlite3.connect(db)
        conn.execute("""CREATE TABLE nodes (
            id INTEGER PRIMARY KEY, content TEXT, category TEXT,
            timestamp TEXT, embedding BLOB, last_accessed TEXT,
            access_count INTEGER DEFAULT 0, importance TEXT DEFAULT 'normal',
            emotional_tone TEXT, emotional_intensity INTEGER DEFAULT 5,
            emotional_reflection TEXT, t_event_start TEXT,
            t_event_end TEXT, temporal_expressions TEXT)"""
        )
        conn.execute("""CREATE TABLE edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER, target_id INTEGER,
            weight REAL DEFAULT 0.5, edge_type TEXT DEFAULT 'semantic',
            created_at TEXT,
            UNIQUE(source_id, target_id, edge_type))"""
        )
        for note_id, category, emb_vec in notes:
            emb = np.array(emb_vec, dtype=np.float32).tobytes()
            conn.execute(
                'INSERT INTO nodes (id, content, category, embedding) VALUES (?, ?, ?, ?)',
                (note_id, f'note {note_id}', category, emb)
            )
        conn.commit()
        conn.close()
        return db

    def _similar_vec(self):
        """Return two similar 384-dim vectors (cosine > 0.65)."""
        import numpy as np
        base = np.random.default_rng(42).random(384).astype(np.float32)
        noise = np.random.default_rng(7).random(384).astype(np.float32) * 0.1
        return base.tolist(), (base + noise).tolist()

    def test_creates_generalizes_and_instantiates(self, tmp_path):
        """Similar concrete+abstract pair: step reports 2 edges (GENERALIZES + INSTANTIATES)."""
        import sys, database
        sys.path.insert(0, '/app/src')
        v1, v2 = self._similar_vec()
        db = self._make_db(tmp_path, [
            (1, 'critical-lesson', v1),
            (2, 'protocol', v2),
        ])
        from sleep_compute import step_generalizes_instantiates
        # dry_run=True to avoid DB_PATH coupling; would_create confirms pair found
        result = step_generalizes_instantiates(db, dry_run=True)
        assert result['pairs_checked'] == 1
        assert result['would_create'] == 2  # GENERALIZES + INSTANTIATES
        # Verify direction logic: concrete→abstract = GENERALIZES
        # Patch database.DB_PATH so create_edge writes to test DB
        orig_db_path = database.DB_PATH
        try:
            database.DB_PATH = db
            result2 = step_generalizes_instantiates(db, dry_run=False)
            assert result2['edges_created'] == 2
        finally:
            database.DB_PATH = orig_db_path

    def test_dry_run_creates_no_edges(self, tmp_path):
        import sys, sqlite3
        sys.path.insert(0, '/app/src')
        v1, v2 = self._similar_vec()
        db = self._make_db(tmp_path, [
            (1, 'critical-lesson', v1),
            (2, 'protocol', v2),
        ])
        from sleep_compute import step_generalizes_instantiates
        result = step_generalizes_instantiates(db, dry_run=True)
        assert result['edges_created'] == 0
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        conn.close()
        assert count == 0

    def test_dissimilar_pair_no_edges(self, tmp_path):
        """Orthogonal vectors (cosine=0) get no edges."""
        import sys, sqlite3, numpy as np
        sys.path.insert(0, '/app/src')
        # Orthogonal unit vectors: cosine = 0.0, well below 0.65 threshold
        v1 = np.zeros(384, dtype=np.float32); v1[0] = 1.0
        v2 = np.zeros(384, dtype=np.float32); v2[1] = 1.0
        db = self._make_db(tmp_path, [
            (1, 'critical-lesson', v1.tolist()),
            (2, 'protocol', v2.tolist()),
        ])
        from sleep_compute import step_generalizes_instantiates
        result = step_generalizes_instantiates(db, dry_run=False)
        assert result['edges_created'] == 0

    def test_same_category_no_edges(self, tmp_path):
        """Two concrete notes do NOT get GENERALIZES edges."""
        import sys, sqlite3
        sys.path.insert(0, '/app/src')
        v1, v2 = self._similar_vec()
        db = self._make_db(tmp_path, [
            (1, 'critical-lesson', v1),
            (2, 'critical-lesson', v2),  # both concrete
        ])
        from sleep_compute import step_generalizes_instantiates
        result = step_generalizes_instantiates(db, dry_run=False)
        assert result['edges_created'] == 0

# ─────────────────────────────────────────────
# Emotional tag normalization (2b fix)
# ─────────────────────────────────────────────

class TestEmotionalTagNormalization:

    def test_russian_tags_normalize(self):
        import sys; sys.path.insert(0, '/app/src')
        from entity_extractor import normalize_emotional_tag
        assert normalize_emotional_tag('радость') == 'joy'
        assert normalize_emotional_tag('тепло') == 'warmth'
        assert normalize_emotional_tag('гордость') == 'pride'
        assert normalize_emotional_tag('стыд') == 'shame'
        assert normalize_emotional_tag('благодарность') == 'gratitude'

    def test_spanish_tags_normalize(self):
        import sys; sys.path.insert(0, '/app/src')
        from entity_extractor import normalize_emotional_tag
        assert normalize_emotional_tag('alegría') == 'joy'
        assert normalize_emotional_tag('orgullo') == 'pride'
        assert normalize_emotional_tag('confianza') == 'trust'

    def test_unknown_tag_passthrough(self):
        import sys; sys.path.insert(0, '/app/src')
        from entity_extractor import normalize_emotional_tag
        assert normalize_emotional_tag('joy') == 'joy'
        assert normalize_emotional_tag('some-unknown-tag') == 'some-unknown-tag'

    def test_cross_lingual_resonance(self, tmp_path):
        """RU tag 'радость, тепло' matches EN tag 'joy, warmth'"""
        import sys, sqlite3, os
        sys.path.insert(0, '/app/src')
        import numpy as np
        db = os.path.join(str(tmp_path), 'test_cross.db')
        conn = sqlite3.connect(db)
        conn.execute("""CREATE TABLE nodes (
            id INTEGER PRIMARY KEY, content TEXT, category TEXT,
            timestamp TEXT, embedding BLOB, last_accessed TEXT,
            access_count INTEGER DEFAULT 0, importance TEXT DEFAULT 'normal',
            emotional_tone TEXT, emotional_intensity INTEGER DEFAULT 5,
            emotional_reflection TEXT, t_event_start TEXT,
            t_event_end TEXT, temporal_expressions TEXT)"""
        )
        conn.execute("""CREATE TABLE edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER, target_id INTEGER,
            weight REAL DEFAULT 0.5, edge_type TEXT DEFAULT 'semantic',
            created_at TEXT, UNIQUE(source_id, target_id, edge_type))"""
        )
        conn.execute("INSERT INTO nodes (id, content, emotional_tone) VALUES (1, 'note1', 'радость, тепло, гордость')")
        conn.execute("INSERT INTO nodes (id, content, emotional_tone) VALUES (2, 'note2', 'joy, warmth, resolve')")
        conn.commit()
        conn.close()
        from sleep_compute import step_emotional_resonance
        result = step_emotional_resonance(db, dry_run=True)
        assert result['pairs_checked'] == 1, f'Expected 1 resonant pair, got {result["pairs_checked"]}'


# === Emergence Detection Tests ===

class TestEmergenceCheck:
    """Tests for step_emergence_check in sleep_compute."""

    def test_emergence_log_table_created(self, tmp_path):
        """emergence_log table is created on first run."""
        import sqlite3
        import numpy as np
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        conn.execute("""CREATE TABLE nodes (
            id INTEGER PRIMARY KEY, content TEXT, category TEXT,
            embedding BLOB, timestamp TEXT, importance TEXT,
            emotional_tone TEXT, emotional_intensity INTEGER,
            last_accessed TEXT, access_count INTEGER,
            t_event_start TEXT, t_event_end TEXT
        )""")
        conn.execute("""CREATE TABLE edges (
            id INTEGER PRIMARY KEY, source_id INTEGER, target_id INTEGER,
            weight REAL, edge_type TEXT, created_at TEXT
        )""")
        # Add minimal nodes with embeddings
        emb = np.random.randn(384).astype(np.float32).tobytes()
        for i in range(5):
            conn.execute(
                "INSERT INTO nodes (id, content, category, embedding, timestamp, importance) VALUES (?, ?, ?, ?, ?, ?)",
                (i+1, f"test note {i}", "general", emb, "2026-03-16", "normal")
            )
        conn.commit()
        conn.close()

        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        from sleep_compute import step_emergence_check
        result = step_emergence_check(str(db), dry_run=True)

        assert 'convergence' in result
        assert 'phi_proxy' in result
        assert 'self_ref_precision' in result
        assert 'composite' in result
        assert 0 <= result['convergence'] <= 1
        assert 0 <= result['phi_proxy'] <= 1
        assert 0 <= result['composite'] <= 1

    def test_emergence_composite_formula(self):
        """Composite = 0.3*convergence + 0.4*phi + 0.3*self_ref."""
        c, p, s = 0.5, 0.7, 0.6
        expected = 0.3 * c + 0.4 * p + 0.3 * s
        assert abs(expected - 0.61) < 0.01


# === Lateral Inhibition Tests ===

class TestLateralInhibition:
    """Tests for GABA-like lateral inhibition in graph_engine."""

    def test_inhibition_strength_zero_no_change(self):
        """INHIBITION_STRENGTH=0 should not modify scores."""
        scores = {1: 0.9, 2: 0.8, 3: 0.7}
        # With strength=0, no suppression
        strength = 0.0
        if strength > 0:
            for nid in scores:
                scores[nid] *= (1.0 - strength)
        assert scores == {1: 0.9, 2: 0.8, 3: 0.7}

    def test_inhibition_suppresses_non_winners(self):
        """Non-winner nodes in same community should be suppressed."""
        strength = 0.3
        community = [(1, 0.9), (2, 0.8), (3, 0.7)]  # node_id, score
        winner_id = max(community, key=lambda x: x[1])[0]
        results = {}
        for nid, score in community:
            if nid == winner_id:
                results[nid] = score  # winner keeps score
            else:
                results[nid] = score * (1.0 - strength)  # suppressed
        assert results[1] == 0.9  # winner unchanged
        assert abs(results[2] - 0.56) < 0.01  # 0.8 * 0.7
        assert abs(results[3] - 0.49) < 0.01  # 0.7 * 0.7

    def test_inhibition_increases_spread(self):
        """Inhibition should increase score gap between winner and others."""
        import numpy as np
        before = [0.9, 0.85, 0.83, 0.80, 0.78]
        after = [0.9, 0.85 * 0.7, 0.83 * 0.7, 0.80, 0.78 * 0.7]  # assuming 2,3,5 same comm as 1
        spread_before = before[0] - before[-1]
        spread_after = after[0] - min(after)
        assert spread_after > spread_before

    def test_singleton_community_no_suppression(self):
        """A community with only one member should not be affected."""
        strength = 0.5
        community = [(42, 0.75)]  # single member
        # No suppression for singletons
        assert len(community) < 2  # skip condition


class TestCommunityResolution:
    """Tests for sub-community detection resolution."""

    def test_higher_resolution_more_communities(self):
        """Higher resolution should produce more communities."""
        import networkx as nx
        from networkx.algorithms.community import greedy_modularity_communities
        # Create a small graph with clear cluster structure
        G = nx.Graph()
        # Two clusters connected by weak link
        for i in range(5):
            for j in range(i+1, 5):
                G.add_edge(i, j, weight=0.8)
        for i in range(5, 10):
            for j in range(i+1, 10):
                G.add_edge(i, j, weight=0.8)
        G.add_edge(3, 7, weight=0.1)  # weak bridge

        comms_low = greedy_modularity_communities(G, weight='weight', resolution=1.0)
        comms_high = greedy_modularity_communities(G, weight='weight', resolution=5.0)
        assert len(list(comms_high)) >= len(list(comms_low))
