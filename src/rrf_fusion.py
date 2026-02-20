"""
Reciprocal Rank Fusion (RRF) — alternative to weighted blend scoring.

Instead of combining raw scores with weights (α×sem + β×spread + γ×BM25 + δ×temporal),
RRF merges ranked lists by rank position. This eliminates score scale mismatch
between different signals.

Formula: RRF_score(d) = Σ 1/(k + rank_r(d)) for each retriever r
where k=60 is a constant that prevents top-ranked docs from dominating.

Reference: Cormack et al. (2009), used by Hindsight/TEMPR (Dec 2025, 89.61% LoCoMo)
"""

import os

RRF_K = int(os.getenv("RRF_K", "60"))  # Standard RRF constant
FUSION_METHOD = os.getenv("FUSION_METHOD", "blend")  # blend | rrf


def rrf_fuse(signal_dicts, k=None):
    """
    Fuse multiple score dictionaries using Reciprocal Rank Fusion.
    
    Args:
        signal_dicts: list of (name, dict) where dict = {node_id: score}
            Only non-empty dicts with scores > 0 contribute rankings.
        k: RRF constant (default: RRF_K from env, typically 60)
    
    Returns:
        dict: {node_id: rrf_score} — higher is better
    """
    if k is None:
        k = RRF_K
    
    fused = {}
    active_signals = 0
    
    for name, scores in signal_dicts:
        if not scores:
            continue
        
        # Sort by score descending to get ranks
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        active_signals += 1
        
        for rank, (node_id, score) in enumerate(ranked):
            if score <= 0:
                break  # Skip zero/negative scores
            rrf_contribution = 1.0 / (k + rank + 1)  # rank is 0-based, +1 for 1-based
            fused[node_id] = fused.get(node_id, 0.0) + rrf_contribution
    
    if active_signals > 0:
        print(f"🔀 RRF fusion (k={k}): {active_signals} signals, {len(fused)} nodes scored")
    
    return fused
