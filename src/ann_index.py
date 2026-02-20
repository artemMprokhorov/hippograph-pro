#!/usr/bin/env python3
"""
ANN (Approximate Nearest Neighbor) Index using hnswlib
Provides O(log n) similarity search with INCREMENTAL updates
"""

import numpy as np
import hnswlib
import os
from typing import List, Tuple, Optional

# Configuration
USE_ANN_INDEX = os.getenv("USE_ANN_INDEX", "true").lower() == "true"
HNSW_SPACE = os.getenv("HNSW_SPACE", "cosine")  # cosine, ip, or l2
HNSW_M = int(os.getenv("HNSW_M", "16"))
HNSW_EF_CONSTRUCTION = int(os.getenv("HNSW_EF_CONSTRUCTION", "200"))
HNSW_EF_SEARCH = int(os.getenv("HNSW_EF_SEARCH", "50"))
MAX_ELEMENTS = int(os.getenv("HNSW_MAX_ELEMENTS", "50000"))


class ANNIndex:
    """hnswlib-based ANN index for fast similarity search with incremental updates."""
    
    def __init__(self, dimension=None):
        if dimension is None:
            dimension = int(os.getenv("EMBEDDING_DIMENSION", "384"))
        self.dimension = dimension
        self.index = None
        self.node_ids = []
        self.enabled = USE_ANN_INDEX
        
        if not self.enabled:
            print("ℹ️  ANN indexing disabled (USE_ANN_INDEX=false)")
            return
        
        # Create HNSW index with cosine similarity
        # space='cosine' - Auto-normalizes and computes cosine similarity
        # space='ip' - Inner product (for pre-normalized vectors)
        # space='l2' - Euclidean distance
        self.index = hnswlib.Index(space=HNSW_SPACE, dim=dimension)
        self.index.init_index(
            max_elements=MAX_ELEMENTS,
            ef_construction=HNSW_EF_CONSTRUCTION,
            M=HNSW_M
        )
        self.index.set_ef(HNSW_EF_SEARCH)
        
        print(f"✅ Created hnswlib {HNSW_SPACE.upper()} index (M={HNSW_M}, ef_construction={HNSW_EF_CONSTRUCTION}, dim={dimension})")
    
    def build(self, nodes: List[dict]) -> int:
        """Build index from nodes with embeddings (initial load)."""
        if not self.enabled or self.index is None:
            return 0
        
        embeddings = []
        node_ids = []
        
        for node in nodes:
            if node.get("embedding") is None:
                continue
            emb = np.frombuffer(node["embedding"], dtype=np.float32)
            if len(emb) != self.dimension:
                continue
            embeddings.append(emb)
            node_ids.append(node["id"])
        
        if not embeddings:
            print("⚠️  No embeddings to index")
            return 0
        
        embeddings_matrix = np.array(embeddings, dtype=np.float32)
        self.index.add_items(embeddings_matrix, node_ids)
        self.node_ids = node_ids
        
        print(f"✅ Built ANN index with {len(embeddings)} vectors")
        return len(embeddings)
    
    def add_vector(self, node_id: int, embedding: np.ndarray) -> bool:
        """Add single vector to index incrementally (NEW!)."""
        if not self.enabled or self.index is None:
            return False
        
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)
        
        try:
            self.index.add_items(embedding, [node_id])
            self.node_ids.append(node_id)
            return True
        except Exception as e:
            print(f"⚠️  Failed to add vector {node_id}: {e}")
            return False
    
    def search(self, query_embedding: np.ndarray, k: int = 10, 
               min_similarity: float = 0.3) -> List[Tuple[int, float]]:
        """Search for k nearest neighbors."""
        if not self.enabled or self.index is None or len(self.node_ids) == 0:
            return []
        
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        try:
            actual_k = min(k, self.index.get_current_count())
            if actual_k == 0:
                return []
            labels, distances = self.index.knn_query(query_embedding, k=actual_k)
            
            results = []
            for label, dist in zip(labels[0], distances[0]):
                if label == -1:  # Invalid result
                    continue
                
                # Convert distance to similarity score
                if HNSW_SPACE == "cosine" or HNSW_SPACE == "ip":
                    similarity = 1.0 - dist  # cosine distance → similarity
                else:  # l2
                    similarity = 1.0 / (1.0 + dist)  # L2 → similarity
                
                if similarity >= min_similarity:
                    results.append((int(label), float(similarity)))
            
            return results
        except Exception as e:
            print(f"⚠️  Search failed: {e}")
            return []
    
    def save(self, path: str):
        """Save index to disk."""
        if not self.enabled or self.index is None:
            return
        
        self.index.save_index(path)
        print(f"💾 Saved ANN index to {path}")
    
    def load(self, path: str):
        """Load index from disk."""
        if not self.enabled or self.index is None:
            return
        
        if not os.path.exists(path):
            print(f"⚠️  Index file not found: {path}")
            return
        
        self.index.load_index(path)
        # Rebuild node_ids list from index
        self.node_ids = self.index.get_ids_list()
        print(f"📂 Loaded ANN index from {path} ({len(self.node_ids)} vectors)")
    
    def get_stats(self) -> dict:
        """Get index statistics."""
        if not self.enabled or self.index is None:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "space": HNSW_SPACE,
            "dimension": self.dimension,
            "vectors": len(self.node_ids),
            "max_elements": MAX_ELEMENTS,
            "M": HNSW_M,
            "ef_construction": HNSW_EF_CONSTRUCTION,
            "ef_search": HNSW_EF_SEARCH
        }


# Global instance
_ann_index = None


def get_ann_index() -> ANNIndex:
    """Get or create global ANN index instance.
    Auto-detects embedding dimension from the loaded model."""
    global _ann_index
    if _ann_index is None:
        try:
            from stable_embeddings import get_model
            dim = get_model().dimension
            print(f"📐 Auto-detected embedding dimension: {dim}")
        except Exception:
            dim = int(os.getenv("EMBEDDING_DIMENSION", "384"))
            print(f"📐 Using configured embedding dimension: {dim}")
        _ann_index = ANNIndex(dimension=dim)
    return _ann_index


def rebuild_index(nodes: List[dict]) -> int:
    """Rebuild index from nodes (called at server startup)."""
    ann_index = get_ann_index()
    return ann_index.build(nodes)
