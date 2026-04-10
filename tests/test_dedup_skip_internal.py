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


def _install_stub_module(name, attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# stable_embeddings: avoid loading BGE-M3
_install_stub_module(
    "stable_embeddings",
    {"get_model": lambda: _stub_model},
)

# entity_extractor: avoid loading GLiNER; tests use skip_ner=True anyway
_install_stub_module(
    "entity_extractor",
    {
        "extract_entities": lambda content: [],
        "normalize_query": lambda q: q,
    },
)


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
    - cos(target,  chunk)  ≈ 0.96   (above DUPLICATE_THRESHOLD, reproduces bug)

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


# ─────────────────────────────────────────────────────────────────────────────
# 3. Base class: fresh temp DB + fresh ANN index per test method
# ─────────────────────────────────────────────────────────────────────────────


class _IsolatedHippoGraphBase:
    """Isolate database, ann_index, and graph_engine state between tests."""

    def setup_method(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.environ["DB_PATH"] = self.db_path

        # Drop stale caches so re-import uses the new DB_PATH / ANN instance
        for mod in ("database", "ann_index", "graph_engine"):
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

        for mod in ("database", "ann_index", "graph_engine"):
            sys.modules.pop(mod, None)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Baseline: documents the pre-fix bug
# ─────────────────────────────────────────────────────────────────────────────


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
