#!/usr/bin/env python3
"""
Graph Metrics for Neural Memory Graph
Computes PageRank and community detection, cached at startup.
"""
import os
import time
from typing import Dict, List, Set, Tuple

# PageRank weight in final scoring (small boost, not dominant)
PAGERANK_BOOST = float(os.getenv("PAGERANK_BOOST", "0.1"))


class GraphMetrics:
    """Cached graph metrics: PageRank scores and community labels."""
    
    def __init__(self):
        self._pagerank: Dict[int, float] = {}
        self._communities: Dict[int, int] = {}  # node_id → community_id
        self._community_sizes: Dict[int, int] = {}
        self._computed_at: float = 0
        self._node_count: int = 0
    
    def compute(self, edges: List[Tuple[int, int, float]], node_ids: List[int]):
        """
        Compute PageRank and communities from edge list.
        Called at startup and after significant graph changes.
        """
        import networkx as nx
        
        start = time.time()
        
        G = nx.DiGraph()
        for nid in node_ids:
            G.add_node(nid)
        for src, tgt, w in edges:
            G.add_edge(src, tgt, weight=w)
        
        # PageRank
        if G.number_of_edges() > 0:
            self._pagerank = nx.pagerank(G, weight='weight', max_iter=100)
        else:
            self._pagerank = {nid: 1.0 / max(len(node_ids), 1) for nid in node_ids}
        
        # Normalize PageRank to 0-1 range
        if self._pagerank:
            max_pr = max(self._pagerank.values())
            if max_pr > 0:
                self._pagerank = {k: v / max_pr for k, v in self._pagerank.items()}
        
        # Community detection (on undirected graph)
        UG = G.to_undirected()
        components = sorted(nx.connected_components(UG), key=len, reverse=True)
        
        if len(components) > 0 and len(components[0]) > 4:
            try:
                from networkx.algorithms.community import greedy_modularity_communities
                largest = UG.subgraph(components[0]).copy()
                comms = greedy_modularity_communities(largest, weight='weight')
                comms = sorted(comms, key=len, reverse=True)
                for comm_id, comm_nodes in enumerate(comms):
                    self._community_sizes[comm_id] = len(comm_nodes)
                    for nid in comm_nodes:
                        self._communities[nid] = comm_id
            except Exception as e:
                print(f"⚠️  Community detection failed: {e}")
        
        # Mark isolated nodes as community -1
        for nid in node_ids:
            if nid not in self._communities:
                self._communities[nid] = -1
        
        self._computed_at = time.time()
        self._node_count = len(node_ids)
        elapsed = time.time() - start
        print(f"📊 Graph metrics computed in {elapsed:.2f}s: "
              f"{len(self._pagerank)} PR scores, "
              f"{len(self._community_sizes)} communities")
    
    def get_pagerank(self, node_id: int) -> float:
        """Get normalized PageRank score (0-1) for a node."""
        return self._pagerank.get(node_id, 0.0)
    
    def get_pagerank_boost(self, node_id: int) -> float:
        """
        Get multiplicative PageRank boost for search scoring.
        Returns 1.0 + PAGERANK_BOOST * normalized_pr
        So top nodes get ~1.1x boost, bottom nodes get ~1.0x.
        """
        pr = self.get_pagerank(node_id)
        return 1.0 + PAGERANK_BOOST * pr
    
    def get_community(self, node_id: int) -> int:
        """Get community ID for a node. -1 = isolated."""
        return self._communities.get(node_id, -1)
    
    def get_stats(self) -> Dict:
        """Get summary statistics for neural_stats tool."""
        return {
            "pagerank_computed": self._computed_at > 0,
            "top_pagerank_nodes": sorted(
                self._pagerank.items(), key=lambda x: -x[1]
            )[:10],
            "communities": len(self._community_sizes),
            "community_sizes": dict(sorted(
                self._community_sizes.items(), key=lambda x: -x[1]
            )[:10]),
            "isolated_nodes": sum(1 for v in self._communities.values() if v == -1),
        }
    
    @property
    def is_computed(self) -> bool:
        return self._computed_at > 0


# Singleton
_metrics = GraphMetrics()


def get_graph_metrics() -> GraphMetrics:
    return _metrics
