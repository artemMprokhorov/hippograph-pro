#!/usr/bin/env python3
"""
Regression tests for duplicate detection false positives from internal categories.

Bug
---
``add_engram_with_links`` in ``src/graph_engine.py`` runs its duplicate check
through ``ann_index.search`` without filtering by node category. The ANN index
contains every node type the engine ever creates, including ``lc-chunk``
children produced by late chunking of earlier notes. Those children are
literal fragments of their parent's text re-embedded for granular retrieval,
so their cosine similarity to any new root-level note about the same topic is
extremely high.

Concretely: adding ``12.02 federated-game architecture`` after ``12.01
federated-game`` (hub) already exists blocks the new note with
``{"error": "duplicate"}`` because the top ANN hit is an lc-chunk of 12.01
at ``similarity = 0.96`` — above ``DUPLICATE_THRESHOLD = 0.95`` — even though
12.02 and the lc-chunk are not the same document.

Fix
---
Exclude derived / internal categories from the duplicate candidate pool. See
``DUPLICATE_CHECK_EXCLUDE`` constant (added by the dedup fix) and the
refactored duplicate check in ``add_engram_with_links``.

Test strategy
-------------
These tests run against an isolated tempfile DB and a fresh ANN index per
method. ``stable_embeddings`` and ``entity_extractor`` are stubbed at the
``sys.modules`` level before importing any hippograph module to avoid loading
BGE-M3 (~2 GB) and GLiNER (~500 MB) in unit tests. Embeddings are hand-built
unit vectors with controlled cosine similarities so the reproduction is
deterministic and fast.

TZ: talkman/technical_tasks/2026-04-10_hippograph_dedup_skip_internal.md
"""

import os
import sys
import tempfile
import types

import numpy as np
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 1. Preempt heavy dependencies BEFORE importing any hippograph module
# ─────────────────────────────────────────────────────────────────────────────

os.environ.setdefault("USE_ANN_INDEX", "true")
os.environ.setdefault("HNSW_SPACE", "cosine")
os.environ.setdefault("EMBEDDING_DIMENSION", "1024")
# Disable pipeline side effects that aren't under test
os.environ["KEYWORD_ANCHOR_ENABLED"] = "false"
os.environ["ONLINE_CONSOLIDATION"] = "false"
os.environ["LATE_CHUNKING_ENABLED"] = "false"


class _StubModel:
    """Deterministic embedding stub. Tests set ``_next_vector`` before each
    encode() call so ``add_engram_with_links`` receives a known vector."""

    dimension = 1024
    _next_vector = None

    def encode(self, text):
        if self._next_vector is None:
            raise RuntimeError("StubModel: _next_vector not set by test")
        return np.array([self._next_vector])


_stub_model = _StubModel()


# List of sys.modules entries these tests stub out. Installed inside
# setup_method so tests that import the real stable_embeddings /
# entity_extractor (in the same pytest session) are not contaminated.
_STUBBED_MODULES = ("stable_embeddings", "entity_extractor")
# List of hippograph modules these tests re-import against the stub set so
# every test gets a fresh ANN index and DB binding.
_REIMPORTED_MODULES = ("database", "ann_index", "graph_engine")


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ─────────────────────────────────────────────────────────────────────────────
# 2. Deterministic embedding construction
# ─────────────────────────────────────────────────────────────────────────────


def _unit(vec):
    n = np.linalg.norm(vec)
    if n == 0:
        return vec.astype(np.float32)
    return (vec / n).astype(np.float32)


def _build_test_vectors(seed=42):
    """Return (parent, target, chunk) unit vectors with these cosine sims:

    - cos(parent,  target) ≈ 0.70
    - cos(parent,  chunk)  ≈ 0.75   (below DUPLICATE_THRESHOLD=0.95)
    - cos(target,  chunk)  ≈ 0.99   (above DUPLICATE_THRESHOLD, reproduces bug)

    ``parent`` stands in for the hub note, ``chunk`` for its lc-chunk child,
    and ``target`` for the distinct root-level note the caller is trying to
    add. The chunk is close to the target but the parent itself is not, so
    without the fix the lc-chunk alone blocks the insertion.
    """
    rng = np.random.default_rng(seed=seed)
    parent = _unit(rng.standard_normal(1024))
    t = _unit(rng.standard_normal(1024))
    target = _unit(0.70 * parent + 0.71 * t)

    # Chunk: strongly aligned with target, tiny parent component, random noise
    chunk_dir = _unit(rng.standard_normal(1024))
    chunk = _unit(0.96 * target + 0.12 * parent + 0.08 * chunk_dir)
    return parent, target, chunk


def _build_close_pair(seed, target_sim=0.97):
    """Return two unit vectors (a, b) with cos(a, b) == target_sim (exact).

    Used for constructing a real near-duplicate between two non-internal
    nodes, so the regression test can verify the duplicate check still
    blocks genuine duplicates after the fix.
    """
    rng = np.random.default_rng(seed=seed)
    a = _unit(rng.standard_normal(1024))
    noise = _unit(rng.standard_normal(1024))
    # Project out the a component so ortho is perpendicular to a
    ortho = noise - float(np.dot(noise, a)) * a
    ortho = _unit(ortho)
    b = _unit(
        target_sim * a + float(np.sqrt(max(0.0, 1.0 - target_sim * target_sim))) * ortho
    )
    return a, b


# ─────────────────────────────────────────────────────────────────────────────
# 3. Base class: fresh temp DB + fresh ANN index per test method
# ─────────────────────────────────────────────────────────────────────────────


class _IsolatedHippoGraphBase:
    """Isolate database, ann_index, and graph_engine state between tests.

    setup_method saves any previously imported stable_embeddings /
    entity_extractor modules, installs lightweight stubs for the duration of
    the test, and re-imports database / ann_index / graph_engine against
    those stubs. teardown_method restores the originals so other tests in
    the same pytest session that rely on the real modules are unaffected.
    """

    def setup_method(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.environ["DB_PATH"] = self.db_path

        # Save any real modules we are about to stub or reimport.
        self._saved_modules = {}
        for name in _STUBBED_MODULES + _REIMPORTED_MODULES:
            self._saved_modules[name] = sys.modules.get(name)

        # Install stubs for heavy dependencies
        stub_se = types.ModuleType("stable_embeddings")
        stub_se.get_model = lambda: _stub_model
        sys.modules["stable_embeddings"] = stub_se

        stub_ee = types.ModuleType("entity_extractor")
        stub_ee.extract_entities = lambda content: []
        stub_ee.normalize_query = lambda q: q
        sys.modules["entity_extractor"] = stub_ee

        # Drop stale caches so re-import uses the new DB_PATH / ANN instance
        for mod in _REIMPORTED_MODULES:
            sys.modules.pop(mod, None)

        import database
        database.DB_PATH = self.db_path
        database.init_database()

        import ann_index
        ann_index._ann_index = None  # force fresh HNSW index

        import graph_engine

        self.database = database
        self.ann_index = ann_index
        self.graph_engine = graph_engine

        _stub_model._next_vector = None

    def teardown_method(self):
        os.close(self.db_fd)
        try:
            os.unlink(self.db_path)
        except Exception:
            pass
        os.environ.pop("DB_PATH", None)

        # Restore whatever was in sys.modules before this test ran. For slots
        # that were empty we clear them so a later test triggers a fresh
        # import of the real module.
        for name, saved in self._saved_modules.items():
            if saved is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved


# ─────────────────────────────────────────────────────────────────────────────
# 4. Baseline: documents the pre-fix bug
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.skip(
    reason="documents pre-fix behavior — kept for audit trail"
)
class TestDedupBaseline(_IsolatedHippoGraphBase):
    """Pre-fix behavior: an lc-chunk blocks a distinct root concept as duplicate.

    After the fix is applied, this test is marked skip — it documents the
    failure mode that motivated the fix and the commit that reproduces it.
    """

    def test_baseline_lc_chunk_blocks_root_concept(self):
        parent_emb, target_emb, chunk_emb = _build_test_vectors()

        parent_id = self.database.create_node(
            "Parent hub page for federated-game architecture.",
            "concept",
            parent_emb.tobytes(),
            "normal",
        )
        chunk_id = self.database.create_node(
            "late-chunking fragment of the parent hub.",
            "lc-chunk",
            chunk_emb.tobytes(),
            "low",
        )

        ann = self.ann_index.get_ann_index()
        assert ann.enabled, "ANN index must be enabled for this test"
        assert ann.dimension == 1024, f"unexpected ANN dim {ann.dimension}"
        ann.add_vector(parent_id, parent_emb)
        ann.add_vector(chunk_id, chunk_emb)

        # Stub model returns ``target_emb`` on the next encode() call.
        _stub_model._next_vector = target_emb

        result = self.graph_engine.add_engram_with_links(
            "New root concept discussing related but distinct architecture.",
            category="concept",
            skip_ner=True,
        )

        # Pre-fix: duplicate error, blocked by lc-chunk (not by the parent).
        assert isinstance(result, dict), f"unexpected return {type(result).__name__}"
        assert "error" in result, (
            "Expected a duplicate error on pre-fix code. "
            f"Got {result!r}. If the fix is already applied this assertion "
            "fails and the test should be marked skip."
        )
        assert result["error"] == "duplicate"
        assert result["existing_id"] == chunk_id, (
            f"Expected block by lc-chunk id={chunk_id}, "
            f"got existing_id={result['existing_id']}. A parent hit would "
            "indicate a different collision mode than the one the fix targets."
        )
        assert result["similarity"] >= 0.95, (
            f"Expected similarity >= 0.95 at the duplicate boundary, "
            f"got {result['similarity']}."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Fix verification
# ─────────────────────────────────────────────────────────────────────────────


class TestDedupFix(_IsolatedHippoGraphBase):
    """Post-fix behavior: a root concept can be added even when an existing
    lc-chunk has near-identical similarity to it."""

    def test_fix_lc_chunk_no_longer_blocks_root_concept(self):
        parent_emb, target_emb, chunk_emb = _build_test_vectors()

        parent_id = self.database.create_node(
            "Parent hub page for federated-game architecture.",
            "concept",
            parent_emb.tobytes(),
            "normal",
        )
        chunk_id = self.database.create_node(
            "late-chunking fragment of the parent hub.",
            "lc-chunk",
            chunk_emb.tobytes(),
            "low",
        )

        ann = self.ann_index.get_ann_index()
        ann.add_vector(parent_id, parent_emb)
        ann.add_vector(chunk_id, chunk_emb)

        _stub_model._next_vector = target_emb

        result = self.graph_engine.add_engram_with_links(
            "New root concept discussing related but distinct architecture.",
            category="concept",
            skip_ner=True,
        )

        # Post-fix: the note is created, not blocked.
        assert "error" not in result, (
            f"Expected success, got error: {result!r}. "
            "The fix should have filtered out the lc-chunk candidate."
        )
        assert "note_id" in result
        assert result["note_id"] not in (parent_id, chunk_id), (
            f"New note_id {result['note_id']} collided with an existing id "
            f"(parent={parent_id}, chunk={chunk_id})."
        )
        # The engine still reports the high-similarity neighbors via the
        # semantic_links + similar_notes warning path — that behavior is
        # outside the fix and should continue to work.
        assert result.get("semantic_links", 0) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 6. Regression: real (non-internal) near-duplicates still get blocked
# ─────────────────────────────────────────────────────────────────────────────


class TestDedupRegression(_IsolatedHippoGraphBase):
    """Two non-internal concepts with cos >= DUPLICATE_THRESHOLD must still be
    detected as a duplicate — the fix must not weaken real duplicate
    detection."""

    def test_real_concept_near_duplicate_still_blocked(self):
        existing_vec, new_vec = _build_close_pair(seed=777, target_sim=0.97)

        existing_id = self.database.create_node(
            "Existing standalone concept about federated training.",
            "concept",
            existing_vec.tobytes(),
            "normal",
        )

        ann = self.ann_index.get_ann_index()
        ann.add_vector(existing_id, existing_vec)

        _stub_model._next_vector = new_vec

        result = self.graph_engine.add_engram_with_links(
            "A genuinely near-duplicate concept about federated training.",
            category="concept",
            skip_ner=True,
        )

        assert "error" in result, (
            f"Expected duplicate error for cos=0.97 near-duplicate, "
            f"got {result!r}. Regression — the fix weakens real dedup."
        )
        assert result["error"] == "duplicate"
        assert result["existing_id"] == existing_id
        assert result["similarity"] >= 0.95


# ─────────────────────────────────────────────────────────────────────────────
# 7. Multi-category: every internal category is skipped from dedup pool
# ─────────────────────────────────────────────────────────────────────────────


class TestDedupMultiCategory(_IsolatedHippoGraphBase):
    """Seed one node in each internal category with high similarity to a new
    target, verify the new note is created because every internal candidate
    is skipped from the duplicate pool."""

    def test_all_internal_categories_skipped(self):
        target_vec, internal_vec = _build_close_pair(
            seed=1000, target_sim=0.97
        )

        internal_cats = [
            "lc-chunk",
            "keyword-anchor",
            "abstract-topic",
            "atomic-fact",
            "metrics-snapshot",
        ]
        internal_ids = {}
        ann = self.ann_index.get_ann_index()
        for i, cat in enumerate(internal_cats):
            nid = self.database.create_node(
                f"Internal node in category {cat}.",
                cat,
                internal_vec.tobytes(),
                "low",
            )
            ann.add_vector(nid, internal_vec)
            internal_ids[cat] = nid

        _stub_model._next_vector = target_vec

        result = self.graph_engine.add_engram_with_links(
            "New root concept surrounded by internal fragments.",
            category="concept",
            skip_ner=True,
        )

        assert "error" not in result, (
            f"Expected success, got error: {result!r}. "
            f"One of {list(internal_ids)} blocked the new note."
        )
        assert "note_id" in result
        assert result["note_id"] not in internal_ids.values()

    def test_exclude_set_matches_known_categories(self):
        """The DUPLICATE_CHECK_EXCLUDE constant must include every category we
        care about — protects against future cat list drift."""
        expected = {
            "lc-chunk",
            "keyword-anchor",
            "abstract-topic",
            "atomic-fact",
            "metrics-snapshot",
        }
        assert self.graph_engine.DUPLICATE_CHECK_EXCLUDE == expected


# ─────────────────────────────────────────────────────────────────────────────
# 8. Force bypass: force=True skips the duplicate check entirely
# ─────────────────────────────────────────────────────────────────────────────


class TestDedupForceBypass(_IsolatedHippoGraphBase):
    """force=True must bypass the duplicate check completely — including for
    genuine non-internal near-duplicates. Backward compatibility with existing
    callers that rely on force=True."""

    def test_force_bypass_creates_even_for_real_duplicate(self):
        existing_vec, new_vec = _build_close_pair(seed=2024, target_sim=0.99)

        existing_id = self.database.create_node(
            "Existing concept that a new call wants to override.",
            "concept",
            existing_vec.tobytes(),
            "normal",
        )

        ann = self.ann_index.get_ann_index()
        ann.add_vector(existing_id, existing_vec)

        _stub_model._next_vector = new_vec

        # Sanity: without force, this would be blocked.
        # (Reset stub for the next call.)
        result_blocked = self.graph_engine.add_engram_with_links(
            "A genuine near-duplicate without force.",
            category="concept",
            skip_ner=True,
            force=False,
        )
        assert result_blocked.get("error") == "duplicate", (
            f"Sanity: without force the call should be blocked, "
            f"got {result_blocked!r}."
        )

        # With force=True, the call must succeed and create a new node.
        _stub_model._next_vector = new_vec
        result_forced = self.graph_engine.add_engram_with_links(
            "A genuine near-duplicate with force=True.",
            category="concept",
            skip_ner=True,
            force=True,
        )
        assert "error" not in result_forced, (
            f"force=True must bypass the duplicate check, got {result_forced!r}"
        )
        assert "note_id" in result_forced
        assert result_forced["note_id"] != existing_id
