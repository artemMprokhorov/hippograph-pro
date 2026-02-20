#!/usr/bin/env python3
"""
Graph Engine for Neural Memory Graph
Implements spreading activation search and automatic linking
"""

import numpy as np
import os
import math
from datetime import datetime
from typing import List, Dict, Any

from database import (
    create_node, get_node, get_all_nodes, touch_node,
    create_edge, get_connected_nodes,
    get_or_create_entity, link_node_to_entity, get_nodes_by_entity,
    get_entity_counts_batch
)
from stable_embeddings import get_model
from entity_extractor import extract_entities
from ann_index import get_ann_index
from graph_cache import get_graph_cache

# Configuration from environment
ACTIVATION_ITERATIONS = int(os.getenv("ACTIVATION_ITERATIONS", "3"))
ACTIVATION_DECAY = float(os.getenv("ACTIVATION_DECAY", "0.7"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
HALF_LIFE_DAYS = float(os.getenv("HALF_LIFE_DAYS", "30"))
MAX_SEMANTIC_LINKS = int(os.getenv("MAX_SEMANTIC_LINKS", "5"))
BLEND_ALPHA = float(os.getenv("BLEND_ALPHA", "0.6"))  # semantic weight
BLEND_GAMMA = float(os.getenv("BLEND_GAMMA", "0.0"))  # BM25 weight (0=disabled, try 0.15)
BLEND_DELTA = float(os.getenv("BLEND_DELTA", "0.0"))  # temporal weight (0=disabled, try 0.1)


def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def recency_factor(last_accessed_str, created_str=None, half_life_days=HALF_LIFE_DAYS):
    """
    Calculate temporal decay factor based on last access time.
    
    Uses last_accessed primarily (when was this note last useful?).
    Falls back to created timestamp if last_accessed not available.
    
    Returns value between 0 and 1:
    - 1.0 = accessed today
    - 0.5 = accessed half_life_days ago
    - 0.25 = accessed 2*half_life_days ago
    """
    # Prefer last_accessed over created timestamp
    timestamp_str = last_accessed_str or created_str
    
    if not timestamp_str:
        return 0.5
    
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        age_days = (datetime.now() - timestamp).days
        
        # Minimum factor to prevent old notes from completely disappearing
        min_factor = 0.1
        decay = 0.5 ** (age_days / half_life_days)
        
        return max(min_factor, decay)
    except:
        return 0.5


def importance_factor(importance, access_count=0):
    """
    Calculate importance multiplier for activation.
    
    Base factors:
    - critical: 1.5x (anchor notes, identity, key decisions)
    - normal: 1.0x (default)
    - low: 0.7x (temporary, noise)
    
    Also applies small boost for frequently accessed notes.
    """
    base_factors = {
        'critical': 1.5,
        'normal': 1.0,
        'low': 0.7
    }
    base = base_factors.get(importance, 1.0)
    
    # Small boost for frequently accessed notes (max +20%)
    # access_count of 10 gives +10%, 20 gives +20%
    access_boost = min(0.2, (access_count or 0) * 0.01)
    
    return base + access_boost


# Deduplication thresholds
DUPLICATE_THRESHOLD = float(os.getenv("DUPLICATE_THRESHOLD", "0.95"))  # Block creation
SIMILAR_THRESHOLD = float(os.getenv("SIMILAR_THRESHOLD", "0.90"))  # Warn about similar


def find_similar_notes(content, threshold=SIMILAR_THRESHOLD, limit=5):
    """
    Find notes similar to given content.
    
    Returns list of (node_id, similarity, content_preview) tuples.
    Useful for deduplication and finding related notes.
    """
    model = get_model()
    query_emb = model.encode(content)[0]
    
    all_nodes = get_all_nodes()
    similarities = []
    
    for node in all_nodes:
        if node["embedding"] is None:
            continue
        
        node_emb = np.frombuffer(node["embedding"], dtype=np.float32)
        sim = cosine_similarity(query_emb, node_emb)
        
        if sim >= threshold:
            similarities.append({
                "id": node["id"],
                "similarity": round(sim, 4),
                "content": node["content"][:200],
                "category": node["category"]
            })
    
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    return similarities[:limit]


def add_note_with_links(content, category="general", importance="normal", force=False,
                        emotional_tone=None, emotional_intensity=5, emotional_reflection=None):
    """
    Add note with automatic entity extraction, linking, and emotional context.
    
    1. Check for duplicates (unless force=True)
    2. Create embedding (includes emotional context if provided)
    3. Extract entities (people, concepts, projects)
    4. Link to other notes sharing same entities
    5. Find semantically similar notes and create edges
    
    Returns dict with node_id and link statistics.
    If duplicate found, returns error with existing note info.
    """
    model = get_model()
    
    # Include emotional context in embedding if provided
    full_text = content
    if emotional_tone or emotional_reflection:
        emotional_context = []
        if emotional_tone:
            emotional_context.append(f"Emotional tone: {emotional_tone}")
        if emotional_reflection:
            emotional_context.append(emotional_reflection)
        full_text = f"{content}\n\n{'. '.join(emotional_context)}"
    
    embedding = model.encode(full_text)[0]
    
    # Get ANN index once (used for both duplicate check and semantic links)
    ann_index = get_ann_index()
    
    # Check for duplicates unless forced
    # OPTIMIZED: Use ANN index for O(log n) instead of O(n) linear scan
    if not force:
        if ann_index.enabled:
            # Fast duplicate check using ANN index
            d = ann_index.search(embedding, k=5, min_similarity=DUPLICATE_THRESHOLD)
            if d:
                eid,sim = d[0]
                en = get_node(eid)
                if en: return {"error": "duplicate", "message": f"Similar note exists ({sim:.2%})", "existing_id": eid, "existing_content": en["content"][:200], "similarity": round(sim, 4)}
        else:
            # Fallback to linear scan if ANN not enabled
            for n in get_all_nodes():
                if n["embedding"] is None: continue
                sim = cosine_similarity(embedding, np.frombuffer(n["embedding"], dtype=np.float32))
                if sim >= DUPLICATE_THRESHOLD: return {"error": "duplicate", "message": f"Similar note exists ({sim:.2%})", "existing_id": n["id"], "existing_content": n["content"][:200], "similarity": round(sim, 4)}
    
    # Create the node with emotional context
    node_id = create_node(content, category, embedding.tobytes(), importance, emotional_tone, emotional_intensity, emotional_reflection)
    
    # Add to ANN index incrementally (enables immediate search for this note)
    if ann_index.enabled:
        ann_index.add_vector(node_id, embedding)
    
    # Update BM25 index
    from bm25_index import get_bm25_index
    bm25 = get_bm25_index()
    if bm25.is_built:
        bm25.add_document(node_id, content)
    
    # Extract entities and create entity-based links
    entities = extract_entities(content)
    entity_links = []
    
    graph_cache = get_graph_cache()  # Get cache for incremental updates
    
    for en,et in entities:
        eid = get_or_create_entity(en, et)
        link_node_to_entity(node_id, eid)
        for r in get_nodes_by_entity(eid):
            if r["id"] != node_id:
                create_edge(node_id, r["id"], weight=0.6, edge_type="entity")
                create_edge(r["id"], node_id, weight=0.6, edge_type="entity")
                if graph_cache.enabled:
                    graph_cache.add_edge(node_id, r["id"], weight=0.6, edge_type="entity")
                entity_links.append(r["id"])
    
    # Find semantically similar notes
    # OPTIMIZED: Use ANN index for O(log n) instead of O(n) linear scan
    semantic_links = []
    similar_warnings = []
    
    if ann_index.enabled:
        # Fast semantic search using ANN index
        # Request 2x candidates to account for self-reference filtering
        sims = [(n,s) for n,s in ann_index.search(embedding, k=MAX_SEMANTIC_LINKS*2, min_similarity=SIMILARITY_THRESHOLD) if n!=node_id]
    else:
        # Fallback to linear scan if ANN not enabled
        sims = []
        for n in get_all_nodes():
            if n["id"]==node_id or n["embedding"] is None: continue
            sim = cosine_similarity(embedding, np.frombuffer(n["embedding"], dtype=np.float32))
            if sim >= SIMILARITY_THRESHOLD: sims.append((n["id"], sim))
        sims.sort(key=lambda x: x[1], reverse=True)
    
    # Create edges for top MAX_SEMANTIC_LINKS similar nodes
    for rid,sim in sims[:MAX_SEMANTIC_LINKS]:
        create_edge(node_id, rid, weight=sim, edge_type="semantic")
        create_edge(rid, node_id, weight=sim, edge_type="semantic")
        if graph_cache.enabled:
            graph_cache.add_edge(node_id, rid, weight=sim, edge_type="semantic")
        semantic_links.append((rid, sim))
        if sim >= SIMILAR_THRESHOLD: similar_warnings.append({"id": rid, "similarity": round(sim, 4)})

    
    result = {
        "node_id": node_id,
        "entities": entities,
        "entity_links": len(set(entity_links)),
        "semantic_links": len(semantic_links)
    }
    
    if similar_warnings:
        result["warning"] = "Similar notes exist"
        result["similar_notes"] = similar_warnings
    
    return result


def search_with_activation(query, limit=5, iterations=ACTIVATION_ITERATIONS, decay=ACTIVATION_DECAY, 
                          category_filter=None, time_after=None, time_before=None, entity_type_filter=None):
    """
    Search using spreading activation algorithm.
    
    1. Compute initial activation from query similarity
    2. Spread activation through graph edges
    3. Apply temporal decay (recent notes score higher)
    4. Return top activated nodes
    
    Args:
        query: Search query string
        limit: Max results to return
        iterations: Spreading activation iterations  
        decay: Activation decay factor
        category_filter: Optional category to filter results (e.g., "breakthrough", "technical")
        time_after: Optional datetime string - only return notes created after this time (ISO format)
        time_before: Optional datetime string - only return notes created before this time (ISO format)
        entity_type_filter: Optional entity type - only return notes containing entities of this type
                           (e.g., "person", "organization", "concept", "location")
    
    This finds notes that are:
    - Semantically similar to query
    - Connected to similar notes through shared entities
    - Recently accessed (recency boost)
    - Optionally filtered by category, time range, and/or entity type
    """
    model = get_model()
    
    # Initialize search logger
    try:
        from search_logger import SearchLogger
        slog = SearchLogger()
        slog.start()
    except Exception:
        slog = None
    
    # Query temporal decomposition: strip temporal signal words for cleaner semantic search
    query_is_temporal = False
    temporal_direction = None
    search_query = query
    try:
        from query_decomposer import decompose_temporal_query
        search_query, query_is_temporal, temporal_direction = decompose_temporal_query(query)
        if query_is_temporal:
            print(f"🕐 Temporal query detected (direction={temporal_direction}): '{query}' → content='{search_query}'")
    except Exception:
        pass
    
    query_emb = model.encode(search_query)[0]
    if slog: slog.mark("embedding")
    
    all_nodes = get_all_nodes()
    
    # Step 1: Initialize activation from semantic similarity
    # Try ANN index first (O(log n)), fallback to linear scan (O(n))
    ann_index = get_ann_index()
    activations = {}
    semantic_sims = {}  # Preserve raw semantic similarities for blend scoring
    
    if ann_index.enabled and len(ann_index.node_ids) > 0:
        # Fast ANN search
        results = ann_index.search(query_emb, k=limit*3, min_similarity=0.0)
        for node_id, sim in results:
            activations[node_id] = sim
            semantic_sims[node_id] = sim
    else:
        # Fallback: linear scan through all nodes
        for node in all_nodes:
            if node["embedding"] is None:
                continue
            node_emb = np.frombuffer(node["embedding"], dtype=np.float32)
            sim = cosine_similarity(query_emb, node_emb)
            if sim >= 0.3:
                activations[node["id"]] = sim
                semantic_sims[node["id"]] = sim
        print(f"⚠️  Linear search: {len(activations)} initial candidates (ANN disabled)")
    
    if slog: slog.mark("ann")
    
    # Step 2: Spreading activation with normalization and damping
    for iteration in range(iterations):
        new_activations = {}
        
        # Spread from activated nodes
        for node_id, activation in activations.items():
            if activation < 0.01:  # Skip very weakly activated nodes
                continue
            
            # Keep original activation (with decay)
            new_activations[node_id] = new_activations.get(node_id, 0) + activation * decay
            
            # Spread to neighbors
            # Use in-memory graph cache (O(1) instead of SQL)
            graph_cache = get_graph_cache()
            neighbors = graph_cache.get_neighbors(node_id)
            for neighbor_id, edge_weight, edge_type in neighbors:
                
                # Spread activation through edge
                spread = activation * edge_weight * decay
                
                # Add to neighbor's activation
                new_activations[neighbor_id] = new_activations.get(neighbor_id, 0) + spread
        
        # Normalization: scale to 0-1 range based on max
        if new_activations:
            max_activation = max(new_activations.values())
            if max_activation > 0:
                for node_id in new_activations:
                    new_activations[node_id] /= max_activation
        
        activations = new_activations
        
        # Debug output
        if activations:
            print(f"  Iteration {iteration+1}: {len(activations)} nodes, max={max(activations.values()):.4f}, sum={sum(activations.values()):.4f}")

    if slog: slog.mark("spreading")

    
    # Step 3: Apply temporal decay and importance scoring
    node_map = {n["id"]: n for n in all_nodes}
    for node_id in activations:
        if node_id in node_map:
            node = node_map[node_id]
            last_accessed = node.get("last_accessed")
            created = node.get("timestamp")
            importance = node.get("importance", "normal")
            access_count = node.get("access_count", 0)
            
            # Apply both factors
            activations[node_id] *= recency_factor(last_accessed, created)
            activations[node_id] *= importance_factor(importance, access_count)
    
    # Step 4: Blend scoring — combine semantic similarity with spreading activation
    # This prevents hub nodes from dominating results regardless of query relevance
    # Normalize spreading activations to 0-1 range for fair blending
    if activations:
        max_spread = max(activations.values())
        if max_spread > 0:
            spread_normalized = {nid: v / max_spread for nid, v in activations.items()}
        else:
            spread_normalized = activations
    else:
        spread_normalized = {}
    
    # Normalize semantic similarities to 0-1 range
    if semantic_sims:
        max_sem = max(semantic_sims.values())
        if max_sem > 0:
            sem_normalized = {nid: v / max_sem for nid, v in semantic_sims.items()}
        else:
            sem_normalized = semantic_sims
    else:
        sem_normalized = {}
    
    # Blend: combine semantic, spreading, BM25, and temporal signals
    # final = α × semantic + β × spreading + γ × BM25 + δ × temporal
    # where β = 1 - α - γ - δ (spreading gets remainder)
    blended = {}
    alpha = BLEND_ALPHA
    gamma = BLEND_GAMMA
    delta = BLEND_DELTA
    beta = max(0.0, 1.0 - alpha - gamma - delta)
    
    # Get BM25 scores if gamma > 0
    bm25_scores = {}
    if gamma > 0:
        from bm25_index import get_bm25_index
        bm25_raw = get_bm25_index().search(query, top_k=100)
        if bm25_raw:
            max_bm25 = max(bm25_raw.values())
            if max_bm25 > 0:
                bm25_scores = {nid: s / max_bm25 for nid, s in bm25_raw.items()}
        print(f"🔍 BM25: {len(bm25_scores)} docs matched")
    
    if slog: slog.mark("bm25")
    
    # Get temporal scores if delta > 0 OR query is temporal
    temporal_scores = {}
    if delta > 0 or query_is_temporal:
        try:
            from temporal_extractor import extract_temporal_expressions, compute_temporal_overlap
            # Date-range overlap scoring (existing)
            query_temporal = extract_temporal_expressions(query)
            if query_temporal["t_event_start"] and query_temporal["t_event_end"]:
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, t_event_start, t_event_end FROM nodes WHERE t_event_start IS NOT NULL")
                    for row in cursor.fetchall():
                        nid, ns, ne = row
                        overlap = compute_temporal_overlap(
                            query_temporal["t_event_start"], query_temporal["t_event_end"], ns, ne)
                        if overlap > 0:
                            temporal_scores[nid] = overlap
                print(f"🕐 Temporal overlap: {len(temporal_scores)} notes matched")
            
            # Temporal ordering score for temporal queries (before/after/when)
            if query_is_temporal and temporal_direction:
                from query_decomposer import compute_temporal_order_score
                # Get timestamps of all candidate nodes
                candidate_ids = set(activations.keys()) | set(bm25_scores.keys())
                if candidate_ids:
                    node_timestamps = {}
                    with get_connection() as conn:
                        cursor = conn.cursor()
                        placeholders = ','.join('?' * len(candidate_ids))
                        cursor.execute(f"SELECT id, timestamp, t_event_start FROM nodes WHERE id IN ({placeholders})", 
                                      list(candidate_ids))
                        for row in cursor.fetchall():
                            nid = row[0]
                            # Prefer t_event_start over ingestion timestamp
                            ts = row[2] if row[2] else row[1]
                            if ts:
                                node_timestamps[nid] = ts
                    
                    all_ts = list(node_timestamps.values())
                    for nid, ts in node_timestamps.items():
                        order_score = compute_temporal_order_score(ts, temporal_direction, all_ts)
                        # Combine: if overlap exists, blend; otherwise use order score
                        existing = temporal_scores.get(nid, 0.0)
                        temporal_scores[nid] = max(existing, order_score)
                    print(f"🕐 Temporal order ({temporal_direction}): {len(node_timestamps)} notes scored")
        except Exception as e:
            print(f"⚠️ Temporal scoring failed: {e}")
    
    # For temporal queries, ensure delta has weight even if env is 0
    effective_delta = delta
    if query_is_temporal and delta == 0:
        effective_delta = 0.15  # Auto-enable temporal signal for temporal queries
        beta = max(0.0, 1.0 - alpha - gamma - effective_delta)
    
    if slog: slog.mark("temporal")
    
    # Collect all node IDs that appear in any signal
    all_node_ids = set(activations.keys()) | set(bm25_scores.keys()) | set(temporal_scores.keys())
    
    # Choose fusion method: weighted blend or RRF
    from rrf_fusion import FUSION_METHOD, rrf_fuse
    
    if FUSION_METHOD == "rrf":
        # RRF: rank-based fusion — no weight tuning needed
        signals = [
            ("semantic", sem_normalized),
            ("spreading", spread_normalized),
            ("bm25", bm25_scores),
            ("temporal", temporal_scores),
        ]
        blended = rrf_fuse(signals)
    else:
        # Weighted blend (default): α×semantic + β×spreading + γ×BM25 + δ×temporal
        for node_id in all_node_ids:
            sem = sem_normalized.get(node_id, 0.0)
            spread = spread_normalized.get(node_id, 0.0)
            bm25 = bm25_scores.get(node_id, 0.0)
            temp = temporal_scores.get(node_id, 0.0)
            blended[node_id] = alpha * sem + beta * spread + gamma * bm25 + effective_delta * temp
    
    print(f"🔀 {FUSION_METHOD.upper()} scoring: {len(blended)} nodes scored")
    
    # Step 5: Apply entity-count penalty to suppress hub notes
    # Notes with many entities are generic (session summaries, milestones)
    # and should be penalized to let specific notes surface
    entity_counts = get_entity_counts_batch()
    for node_id in blended:
        ec = entity_counts.get(node_id, 0)
        if ec > 20:  # Only penalize true hub notes (25-42 entities)
            blended[node_id] *= 20.0 / ec  # Linear penalty: 0.8 at 25, 0.48 at 42
    
    # Step 6: PageRank boost (informational only, not applied to scoring)
    # Testing showed PAGERANK_BOOST > 0 causes P@5 regression
    # PageRank is available via neural_stats for analysis
    
    # Step 6.5: Cross-encoder reranking (optional)
    # Rerank top-N candidates using cross-encoder for improved precision
    from reranker import get_reranker, RERANK_ENABLED, RERANK_TOP_N
    if RERANK_ENABLED:
        reranker = get_reranker()
        if reranker.is_available:
            # Get top-N candidates with their content for reranking
            pre_sorted = sorted(blended.items(), key=lambda x: x[1], reverse=True)[:RERANK_TOP_N]
            rerank_candidates = []
            for node_id, score in pre_sorted:
                node = node_map.get(node_id)
                content = node.get("content", "") if node else ""
                rerank_candidates.append((node_id, score, content))
            
            # Rerank and update blended scores
            reranked = reranker.rerank(query, rerank_candidates, top_k=RERANK_TOP_N)
            for node_id, new_score in reranked:
                blended[node_id] = new_score
    
    if slog: slog.mark("rerank")
    
    # Step 7: Sort and return top results
    sorted_nodes = sorted(blended.items(), key=lambda x: x[1], reverse=True)
    
    # Debug: check if new notes are in node_map
    for node_id, _ in sorted_nodes[:10]:
        if node_id not in node_map:
            print(f"⚠️  NODE {node_id} in blended but NOT in node_map")
            break
    
    results = []
    for node_id, activation in sorted_nodes:
        node = node_map.get(node_id)
        if not node:
            continue
            
        # Filter by category if specified
        if category_filter and node.get("category") != category_filter:
            continue
        
        # Filter by time range if specified
        if time_after or time_before:
            node_timestamp = node.get("timestamp")
            if node_timestamp:
                if time_after and node_timestamp < time_after:
                    continue
                if time_before and node_timestamp > time_before:
                    continue
        
        # Filter by entity type if specified
        if entity_type_filter:
            # Check if node has any entities of the specified type
            conn = get_db()
            has_entity_type = conn.execute("""
                SELECT 1 FROM node_entities ne
                JOIN entities e ON ne.entity_id = e.id
                WHERE ne.node_id = ? AND e.entity_type = ?
                LIMIT 1
            """, (node_id, entity_type_filter)).fetchone()
            conn.close()
            
            if not has_entity_type:
                continue
            
        # Update access tracking
        touch_node(node_id)
        results.append({
            "id": node_id,
            "content": node["content"],
            "category": node["category"],
            "activation": round(activation, 4),
            "timestamp": node.get("timestamp"),
            "importance": node.get("importance", "normal"),
            "emotional_tone": node.get("emotional_tone"),
            "emotional_intensity": node.get("emotional_intensity", 5)
        })
        
        # Stop when we have enough results
        if len(results) >= limit:
            break
    
    # Include total activated count for context awareness
    total_activated = len(blended)
    
    # Log search metrics
    if slog:
        slog.mark("filters")
        slog.finish(query, results, total_activated, 
            params={
                "query_cleaned": search_query if search_query != query else None,
                "is_temporal": query_is_temporal,
                "temporal_direction": temporal_direction,
                "limit": limit,
                "category_filter": category_filter,
                "time_after": time_after,
                "time_before": time_before,
                "entity_type_filter": entity_type_filter,
            },
            signals={
                "alpha": alpha, "beta": beta, "gamma": gamma, "delta": effective_delta,
                "bm25_matches": len(bm25_scores),
                "temporal_matches": len(temporal_scores),
                "rerank_enabled": RERANK_ENABLED,
            })
    
    return results, total_activated


def get_node_graph(node_id):
    """Get graph visualization data for a specific node"""
    node = get_node(node_id)
    if not node:
        return {"error": "Node not found"}
    
    connected = get_connected_nodes(node_id)
    
    return {
        "node": {
            "id": node_id,
            "content": node["content"][:100],
            "category": node["category"]
        },
        "connections": [
            {
                "id": c["id"],
                "content": c["content"][:100] if c.get("content") else "",
                "weight": c.get("weight", 0.5),
                "type": c.get("edge_type", "unknown")
            }
            for c in connected
        ]
    }
"""
Context Window Protection implementation for search_with_activation

Changes:
1. Added max_results parameter (hard limit, default: 10)
2. Added detail_mode parameter ("brief" | "full", default: "full")
3. Token counting for results
4. Brief mode: returns id, category, first 200 chars, activation

Philosophy: NO summarization (lossy), only truncation (user controls detail)
"""

def format_result_brief(result):
    """Format result in brief mode - first line + metadata for quick scanning"""
    content = result["content"]
    # Get first meaningful line (skip empty lines)
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    first_line = lines[0] if lines else content[:100]
    # Cap at 150 chars
    if len(first_line) > 150:
        first_line = first_line[:147] + "..."
    
    brief = {
        "id": result["id"],
        "category": result["category"],
        "first_line": first_line,
        "activation": result["activation"],
        "timestamp": result.get("timestamp"),
        "importance": result.get("importance", "normal"),
        "full_length": len(content),
        "total_lines": len(lines)
    }
    
    # Add emotional context if present
    if result.get("emotional_tone"):
        brief["emotional_tone"] = result["emotional_tone"]
    if result.get("emotional_intensity") and result["emotional_intensity"] != 5:
        brief["emotional_intensity"] = result["emotional_intensity"]
    
    return brief

def estimate_tokens(text):
    """Rough token estimation: ~4 chars per token"""
    return len(text) // 4

def search_with_activation_protected(query, limit=5, max_results=10, detail_mode="full",
                                   iterations=ACTIVATION_ITERATIONS, decay=ACTIVATION_DECAY, 
                                   category_filter=None, time_after=None, time_before=None, 
                                   entity_type_filter=None):
    """
    Search with context window protection.
    
    NEW Parameters:
        max_results: Hard limit on results returned (default: 10)
                    Overrides 'limit' if limit > max_results
        detail_mode: "brief" (first line + metadata) or "full" (complete content)
                    Default: "full"
    
    Returns:
        {
            "results": [...],
            "metadata": {
                "total_activated": int,  # How many nodes were activated
                "returned": int,          # How many returned
                "detail_mode": str,       # "brief" or "full"
                "estimated_tokens": int,  # Rough token count
                "truncated": bool         # True if total_activated > returned
            }
        }
    
    Brief mode returns:
        - id, category, preview (200 chars), activation, timestamp
        - full_length (original content length)
        - truncated flag
    
    Full mode returns:
        - id, category, content (complete), activation, timestamp
    """
    
    # Enforce max_results hard limit
    effective_limit = min(limit, max_results)
    
    # Get results from original search_with_activation
    raw_results, total_activated = search_with_activation(
        query=query,
        limit=effective_limit,
        iterations=iterations,
        decay=decay,
        category_filter=category_filter,
        time_after=time_after,
        time_before=time_before,
        entity_type_filter=entity_type_filter
    )
    
    # Format based on detail mode
    if detail_mode == "brief":
        formatted_results = [format_result_brief(r) for r in raw_results]
        total_chars = sum(len(r["first_line"]) for r in formatted_results)
    else:
        formatted_results = raw_results
        total_chars = sum(len(r["content"]) for r in formatted_results)
    
    # Metadata
    metadata = {
        "total_activated": total_activated,
        "returned": len(formatted_results),
        "detail_mode": detail_mode,
        "estimated_tokens": estimate_tokens(str(formatted_results)),
        "truncated": total_activated > len(formatted_results),
        "has_more": total_activated > len(formatted_results)
    }
    
    return {
        "results": formatted_results,
        "metadata": metadata
    }
