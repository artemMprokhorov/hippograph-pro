#!/usr/bin/env python3
"""
Baseline Retrieval Servers for HippoGraph LOCOMO Benchmark Comparison.

Two backends implementing the same REST API as HippoGraph:
  POST /api/add_note?api_key=KEY  {"content": "...", "category": "..."}
  GET  /api/search?api_key=KEY&q=...&limit=5
  GET  /health
  DELETE /api/reset?api_key=KEY   (clear all notes for clean run)

Backends:
  --mode bm25    Pure BM25 keyword search (rank-bm25)
  --mode cosine  Pure cosine semantic similarity (sentence-transformers, no graph)

Usage:
  python baseline_server.py --mode bm25   --port 5020
  python baseline_server.py --mode cosine --port 5021

These are ablation baselines to show the contribution of
HippoGraph's spreading activation and graph structure.
"""

import os
import json
import time
import argparse
import re
from flask import Flask, request, jsonify

API_KEY = os.getenv("BASELINE_API_KEY", "benchmark_key_locomo_2026")

# ─────────────────────────────────────────────────────────────
# In-memory store (shared by both backends)
# ─────────────────────────────────────────────────────────────
notes = []
next_id = 1


def reset_store():
    global notes, next_id
    notes = []
    next_id = 1


def add_note(content, category="general"):
    global next_id
    notes.append({"id": next_id, "content": content, "category": category})
    next_id += 1
    return next_id - 1


# ─────────────────────────────────────────────────────────────
# BM25 backend
# ─────────────────────────────────────────────────────────────
def tokenize(text):
    return re.findall(r'\w+', text.lower())


def search_bm25(query, top_k=5):
    if not notes:
        return []
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        raise RuntimeError("rank_bm25 not installed: pip install rank-bm25")

    corpus = [tokenize(n["content"]) for n in notes]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(tokenize(query))

    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
    return [
        {
            "id": notes[i]["id"],
            "content": notes[i]["content"],
            "category": notes[i]["category"],
            "score": float(s)
        }
        for i, s in ranked if s > 0
    ]


# ─────────────────────────────────────────────────────────────
# Cosine backend
# ─────────────────────────────────────────────────────────────
_embed_model = None
_embeddings = []


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        print(f"Loading embedding model: {model_name}")
        _embed_model = SentenceTransformer(model_name)
        print("✅ Embedding model loaded")
    return _embed_model


def add_note_cosine(content, category="general"):
    import numpy as np
    nid = add_note(content, category)
    model = get_embed_model()
    emb = model.encode(content, normalize_embeddings=True)
    _embeddings.append(emb)
    return nid


def search_cosine(query, top_k=5):
    import numpy as np
    if not notes:
        return []
    model = get_embed_model()
    q_emb = model.encode(query, normalize_embeddings=True)
    matrix = np.array(_embeddings)
    scores = matrix @ q_emb
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
    return [
        {
            "id": notes[i]["id"],
            "content": notes[i]["content"],
            "category": notes[i]["category"],
            "score": float(s)
        }
        for i, s in ranked
    ]


def reset_cosine():
    global _embeddings
    _embeddings = []
    reset_store()


# ─────────────────────────────────────────────────────────────
# Flask app factory
# ─────────────────────────────────────────────────────────────
def make_app(mode: str) -> Flask:
    app = Flask(__name__)
    app.config["MODE"] = mode

    def check_key():
        key = request.args.get("api_key") or request.headers.get("X-API-Key")
        if key != API_KEY:
            return jsonify({"error": "unauthorized"}), 401
        return None

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "mode": mode, "notes": len(notes)})

    @app.post("/api/add_note")
    def api_add_note():
        err = check_key()
        if err:
            return err
        data = request.get_json(force=True)
        content = data.get("content", "").strip()
        category = data.get("category", "general")
        if not content:
            return jsonify({"error": "empty content"}), 400
        t0 = time.time()
        if mode == "cosine":
            nid = add_note_cosine(content, category)
        else:
            nid = add_note(content, category)
        elapsed = time.time() - t0
        return jsonify({"id": nid, "elapsed_ms": round(elapsed * 1000, 1)})

    @app.get("/api/search")
    def api_search():
        err = check_key()
        if err:
            return err
        query = request.args.get("q", "").strip()
        top_k = int(request.args.get("limit", 5))
        if not query:
            return jsonify({"error": "empty query"}), 400
        t0 = time.time()
        if mode == "bm25":
            results = search_bm25(query, top_k)
        else:
            results = search_cosine(query, top_k)
        elapsed = time.time() - t0
        return jsonify({
            "results": results,
            "total": len(results),
            "elapsed_ms": round(elapsed * 1000, 1)
        })

    @app.delete("/api/reset")
    def api_reset():
        err = check_key()
        if err:
            return err
        if mode == "cosine":
            reset_cosine()
        else:
            reset_store()
        return jsonify({"status": "reset", "mode": mode})

    return app


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baseline retrieval server for LOCOMO benchmark")
    parser.add_argument("--mode", choices=["bm25", "cosine"], required=True)
    parser.add_argument("--port", type=int, default=5020)
    args = parser.parse_args()

    print(f"🚀 Baseline server — mode={args.mode} port={args.port}")
    if args.mode == "cosine":
        print("⏳ Pre-loading embedding model...")
        get_embed_model()

    app = make_app(args.mode)
    app.run(host="0.0.0.0", port=args.port, debug=False)
