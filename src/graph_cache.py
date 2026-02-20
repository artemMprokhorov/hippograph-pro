#!/usr/bin/env python3
"""
In-Memory Graph Cache for Fast Edge Traversal
Eliminates SQLite bottleneck in spreading activation
"""
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class GraphCache:
    """
    In-memory cache of graph structure (edges)
    
    Structure: {node_id: [(neighbor_id, weight, edge_type), ...]}
    """
    
    def __init__(self):
        self.edges: Dict[int, List[Tuple[int, float, str]]] = defaultdict(list)
        self.enabled = True
        self.edge_count = 0
    
    def build(self, all_edges: List[dict]) -> int:
        """
        Build cache from all edges
        
        Args:
            all_edges: List of edge dicts with source_id, target_id, weight, edge_type
        
        Returns:
            Number of edges cached
        """
        self.edges.clear()
        self.edge_count = 0
        
        for edge in all_edges:
            source_id = edge["source_id"]
            target_id = edge["target_id"]
            weight = edge.get("weight", 0.5)
            edge_type = edge.get("edge_type", "semantic")
            
            # Bidirectional: source -> target and target -> source
            self.edges[source_id].append((target_id, weight, edge_type))
            self.edges[target_id].append((source_id, weight, edge_type))
            
            self.edge_count += 1
        
        print(f"✅ Built graph cache: {self.edge_count} edges, {len(self.edges)} nodes")
        return self.edge_count
    
    def get_neighbors(self, node_id: int) -> List[Tuple[int, float, str]]:
        """
        Get all neighbors of a node (O(1) lookup)
        
        Args:
            node_id: Node to get neighbors for
        
        Returns:
            List of (neighbor_id, weight, edge_type) tuples
        """
        return self.edges.get(node_id, [])
    
    def add_edge(self, source_id: int, target_id: int, weight: float = 0.5, edge_type: str = "semantic"):
        """
        Add edge to cache (for incremental updates)
        
        Args:
            source_id: Source node
            target_id: Target node
            weight: Edge weight
            edge_type: Type of edge
        """
        # Bidirectional
        self.edges[source_id].append((target_id, weight, edge_type))
        self.edges[target_id].append((source_id, weight, edge_type))
        self.edge_count += 1
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        return {
            "enabled": self.enabled,
            "edge_count": self.edge_count,
            "node_count": len(self.edges),
            "avg_degree": self.edge_count * 2 / len(self.edges) if self.edges else 0
        }


# Global singleton
_global_cache: Optional[GraphCache] = None


def get_graph_cache() -> GraphCache:
    """Get or create global graph cache"""
    global _global_cache
    if _global_cache is None:
        _global_cache = GraphCache()
        
        # Auto-build if empty
        if _global_cache.edge_count == 0:
            from database import get_all_edges
            edges = get_all_edges()
            _global_cache.build(edges)
    
    return _global_cache


def rebuild_graph_cache(edges: List[dict]) -> int:
    """Rebuild global graph cache"""
    cache = get_graph_cache()
    return cache.build(edges)
