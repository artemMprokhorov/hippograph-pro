"""
BGE-M3 Sparse Retrieval Index for HippoGraph.

Uses BGE-M3 lexical weights (token-level ReLU activations)
as sparse vectors for exact and near-exact token matching.

License: BAAI/bge-m3 = MIT
Purpose: Find numeric facts ('52.6', '0.717') not found by dense ANN.
"""
import os
import numpy as np
from typing import Dict, List, Tuple

SPARSE_ENABLED = os.environ.get('SPARSE_ENABLED', 'false').lower() == 'true'
SPARSE_MODEL = os.environ.get('SPARSE_MODEL', 'BAAI/bge-m3')
SPARSE_TOP_K = int(os.environ.get('SPARSE_TOP_K', '50'))
BLEND_SPARSE = float(os.environ.get('BLEND_SPARSE', '0.2'))

_model = None
_tokenizer = None
_sparse_vectors: Dict[int, Dict[int, float]] = {}  # node_id -> {token_id: weight}
_is_built = False


def _get_model():
    global _model, _tokenizer
    if _model is None and SPARSE_ENABLED:
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            print(f'Loading BGE-M3 sparse: {SPARSE_MODEL}')
            _tokenizer = AutoTokenizer.from_pretrained(SPARSE_MODEL)
            _model = AutoModel.from_pretrained(SPARSE_MODEL)
            _model.eval()
            print('BGE-M3 sparse loaded')
        except Exception as e:
            print(f'BGE-M3 sparse load failed: {e}')
    return _model, _tokenizer


def _encode_sparse(texts: List[str]) -> List[Dict[int, float]]:
    """Encode texts into sparse token-weight dicts."""
    import torch
    model, tokenizer = _get_model()
    if model is None:
        return [{} for _ in texts]

    results = []
    batch_size = 32
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        inputs = tokenizer(
            batch, return_tensors='pt',
            padding=True, truncation=True, max_length=512
        )
        with torch.no_grad():
            out = model(**inputs)

        # Lexical weights: ReLU on hidden states, then max-pool over tokens
        # Shape: (batch, seq_len, vocab_size) - but we use token_ids directly
        # Simpler: use token_id -> max_weight mapping
        hidden = out.last_hidden_state  # (batch, seq, hidden)
        weights = torch.relu(hidden).max(dim=2).values  # (batch, seq)

        input_ids = inputs['input_ids']  # (batch, seq)
        attention_mask = inputs['attention_mask']  # (batch, seq)

        for b in range(len(batch)):
            sparse = {}
            for pos in range(input_ids.shape[1]):
                if attention_mask[b, pos] == 0:
                    continue
                tid = int(input_ids[b, pos])
                w = float(weights[b, pos])
                if w > 0.1:  # threshold
                    if tid not in sparse or sparse[tid] < w:
                        sparse[tid] = w
            results.append(sparse)

    return results


def build(nodes: List[dict]) -> int:
    """Build sparse index from nodes."""
    global _sparse_vectors, _is_built
    if not SPARSE_ENABLED:
        return 0

    model, tokenizer = _get_model()
    if model is None:
        return 0

    texts = [n.get('content', '')[:512] for n in nodes]
    node_ids = [n['id'] for n in nodes]

    print(f'Building BGE-M3 sparse index for {len(nodes)} nodes...')
    sparse_vecs = _encode_sparse(texts)

    _sparse_vectors = {}
    for nid, svec in zip(node_ids, sparse_vecs):
        if svec:
            _sparse_vectors[nid] = svec

    _is_built = True
    print(f'Sparse index built: {len(_sparse_vectors)} nodes indexed')
    return len(_sparse_vectors)


def add_document(node_id: int, content: str):
    """Add single document to sparse index."""
    if not SPARSE_ENABLED or not _is_built:
        return
    svecs = _encode_sparse([content[:512]])
    if svecs and svecs[0]:
        _sparse_vectors[node_id] = svecs[0]


def search(query: str, top_k: int = SPARSE_TOP_K) -> Dict[int, float]:
    """
    Sparse retrieval: dot product between query sparse vec and doc sparse vecs.
    Returns {node_id: score} for top_k matches.
    """
    if not SPARSE_ENABLED or not _sparse_vectors:
        return {}

    query_vecs = _encode_sparse([query])
    if not query_vecs or not query_vecs[0]:
        return {}

    qvec = query_vecs[0]
    scores = {}

    for nid, dvec in _sparse_vectors.items():
        score = sum(qvec.get(tid, 0.0) * w for tid, w in dvec.items())
        if score > 0:
            scores[nid] = score

    if not scores:
        return {}

    # Normalize
    max_score = max(scores.values())
    if max_score > 0:
        scores = {nid: s / max_score for nid, s in scores.items()}

    # Top-K
    top = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
    return dict(top)


def is_enabled() -> bool:
    return SPARSE_ENABLED and _is_built