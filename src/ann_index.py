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
        skipped_dim = []
        
        for node in nodes:
            if node.get("embedding") is None:
                continue
            emb = np.frombuffer(node["embedding"], dtype=np.float32)
            if len(emb) != self.dimension:
                skipped_dim.append((node["id"], len(emb)))
                continue
            embeddings.append(emb)
            node_ids.append(node["id"])
        
        if skipped_dim:
            print(f"⚠️  Skipped {len(skipped_dim)} nodes with wrong embedding dim (expected {self.dimension}): ids={[n for n,d in skipped_dim[:10]]}")
            print("   Run fix_dimension_mismatch() to repair these nodes.")

        if not embeddings:
            print("⚠️  No embeddings to index")
            return 0
        
        embeddings_matrix = np.array(embeddings, dtype=np.float32)
        self.index.add_items(embeddings_matrix, node_ids)
        self.node_ids = node_ids
        
        print(f"✅ Built ANN index with {len(embeddings)} vectors")
        return len(embeddings)
    
    def add_vector(self, node_id: int, embedding: np.ndarray) -> bool:
        """Add single vector to index incrementally."""
        if not self.enabled or self.index is None:
            return False
        
        if embedding.ndim == 2:
            emb_flat = embedding[0]
        else:
            emb_flat = embedding

        if len(emb_flat) != self.dimension:
            print(f"⚠️  Rejected vector for node {node_id}: dim={len(emb_flat)}, expected {self.dimension}. Recalculating...")
            try:
                from stable_embeddings import get_model
                # We don't have content here, caller must handle this case
                # Just refuse to add a broken vector silently
                return False
            except Exception:
                return False

        embedding_2d = emb_flat.reshape(1, -1)
        try:
            self.index.add_items(embedding_2d, [node_id])
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
                if label == -1:
                    continue
                
                if HNSW_SPACE == "cosine" or HNSW_SPACE == "ip":
                    similarity = 1.0 - dist
                else:
                    similarity = 1.0 / (1.0 + dist)
                
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


def fix_dimension_mismatch(db_path: str = None) -> int:
    """
    Scan DB for nodes with wrong embedding dimension and recompute using our model.
    Returns number of fixed nodes. Called automatically at server startup.
    """
    import sqlite3
    from stable_embeddings import get_model

    ann_index = get_ann_index()
    expected_dim = ann_index.dimension
    model = get_model()

    if db_path is None:
        db_path = os.getenv("DB_PATH", "/app/data/memory.db")

    fixed = 0
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, content, embedding FROM nodes").fetchall()

        to_fix = []
        for row in rows:
            # FIX: If embedding is missing (NULL), add to fix list instead of skipping
            if row["embedding"] is None:
                to_fix.append((row["id"], row["content"]))
                continue

            emb = np.frombuffer(row["embedding"], dtype=np.float32)
            if len(emb) != expected_dim:
                to_fix.append((row["id"], row["content"]))

        if not to_fix:
            return 0

        print(f"🔧 fix_dimension_mismatch: found {len(to_fix)} nodes to repair, recomputing...")
        for node_id, content in to_fix:
            try:
                new_emb = model.encode(content)[0]
                conn.execute("UPDATE nodes SET embedding=? WHERE id=?", (new_emb.tobytes(), node_id))
                # Add to live index
                ann_index.add_vector(node_id, new_emb)
                fixed += 1
                print(f"   ✅ Repaired node #{node_id}")
            except Exception as e:
                print(f"   ❌ Failed to repair node #{node_id}: {e}")

        conn.commit()
        conn.close()

        if fixed:
            print(f"✅ fix_dimension_mismatch: repaired {fixed} nodes")

    except Exception as e:
        print(f"⚠️  fix_dimension_mismatch error: {e}")

    return fixed