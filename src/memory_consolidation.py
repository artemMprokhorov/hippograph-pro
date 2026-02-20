"""
Memory Consolidation - linking related notes without compression

Creates semantic connections between related notes to improve:
- Thematic clustering (related topics)
- Temporal chains (progression over time)
- Conceptual hierarchies (parent-child relationships)
- Cross-references (lessons, breakthroughs, implementations)

CRITICAL: This is NOT compression. Original notes preserved intact.
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import numpy as np


class MemoryConsolidator:
    """
    Consolidates memories by creating explicit semantic links.
    Preserves all original content - no compression or deletion.
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def find_thematic_clusters(self, min_similarity=0.75, min_cluster_size=3):
        """
        Find groups of notes about same theme via semantic similarity.
        
        Returns: List of clusters, each cluster is list of note_ids
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all notes with embeddings
        cursor.execute("""
            SELECT id, content, embedding, category 
            FROM nodes 
            WHERE embedding IS NOT NULL
        """)
        notes = cursor.fetchall()
        
        clusters = []
        processed = set()
        
        for i, (note_id, content, emb_blob, category) in enumerate(notes):
            if note_id in processed:
                continue
                
            # Start new cluster
            cluster = [note_id]
            emb1 = np.frombuffer(emb_blob, dtype=np.float32)
            
            # Find similar notes
            for j, (other_id, _, other_emb_blob, _) in enumerate(notes[i+1:], start=i+1):
                if other_id in processed:
                    continue
                    
                emb2 = np.frombuffer(other_emb_blob, dtype=np.float32)
                similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                
                if similarity >= min_similarity:
                    cluster.append(other_id)
                    processed.add(other_id)
            
            if len(cluster) >= min_cluster_size:
                clusters.append(cluster)
                processed.add(note_id)
        
        conn.close()
        return clusters
    
    def find_temporal_chains(self, max_gap_days=7):
        """
        Find sequences of related notes over time.
        
        Examples:
        - session-end → session-start → session-progress
        - problem → solution → verification
        
        Returns: List of chains, each chain is list of (note_id, timestamp)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get notes sorted by time
        cursor.execute("""
            SELECT id, timestamp, category, content
            FROM nodes
            ORDER BY timestamp
        """)
        notes = cursor.fetchall()
        
        chains = []
        
        # Group by category first (sessions, projects, etc)
        category_groups = {}
        for note_id, timestamp, category, content in notes:
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append((note_id, timestamp, content))
        
        # Find chains within each category
        for category, group in category_groups.items():
            if len(group) < 2:
                continue
            
            chain = []
            for i, (note_id, timestamp, content) in enumerate(group):
                if not chain:
                    chain.append((note_id, timestamp))
                    continue
                
                # Check time gap from last in chain
                last_time = datetime.fromisoformat(chain[-1][1])
                curr_time = datetime.fromisoformat(timestamp)
                gap = (curr_time - last_time).days
                
                if gap <= max_gap_days:
                    chain.append((note_id, timestamp))
                else:
                    # Save current chain if long enough
                    if len(chain) >= 3:
                        chains.append(chain)
                    chain = [(note_id, timestamp)]
            
            # Save last chain
            if len(chain) >= 3:
                chains.append(chain)
        
        conn.close()
        return chains
    
    def create_consolidation_links(self, clusters, chains):
        """
        Create explicit consolidation edges in database.
        Edge type: 'consolidation'
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        created = 0
        
        # Create cluster links (all-to-all within cluster)
        for cluster in clusters:
            for i, node1 in enumerate(cluster):
                for node2 in cluster[i+1:]:
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO edges 
                            (source_id, target_id, edge_type, weight, created_at)
                            VALUES (?, ?, 'consolidation', 0.9, ?)
                        """, (node1, node2, datetime.now().isoformat()))
                        created += cursor.rowcount
                    except:
                        pass
        
        # Create chain links (sequential)
        for chain in chains:
            for i in range(len(chain) - 1):
                node1_id = chain[i][0]
                node2_id = chain[i+1][0]
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO edges 
                        (source_id, target_id, edge_type, weight, created_at)
                        VALUES (?, ?, 'temporal_chain', 0.95, ?)
                    """, (node1_id, node2_id, datetime.now().isoformat()))
                    created += cursor.rowcount
                except:
                    pass
        
        conn.commit()
        conn.close()
        return created


def run_consolidation(db_path, similarity_threshold=0.75, max_gap_days=7):
    """
    Main function to run memory consolidation.
    
    Args:
        db_path: Path to memory.db
        similarity_threshold: Min similarity for thematic clusters
        max_gap_days: Max days between notes in temporal chain
    
    Returns:
        dict with stats
    """
    consolidator = MemoryConsolidator(db_path)
    
    print("🔍 Finding thematic clusters...")
    clusters = consolidator.find_thematic_clusters(
        min_similarity=similarity_threshold,
        min_cluster_size=3
    )
    print(f"   Found {len(clusters)} thematic clusters")
    
    print("🔍 Finding temporal chains...")
    chains = consolidator.find_temporal_chains(max_gap_days=max_gap_days)
    print(f"   Found {len(chains)} temporal chains")
    
    print("🔗 Creating consolidation links...")
    links_created = consolidator.create_consolidation_links(clusters, chains)
    print(f"   Created {links_created} consolidation edges")
    
    return {
        'clusters': len(clusters),
        'chains': len(chains),
        'links_created': links_created,
        'cluster_details': clusters,
        'chain_details': chains
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python memory_consolidation.py <path_to_memory.db>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    results = run_consolidation(db_path)
    
    print("\n✅ Consolidation complete!")
    print(f"   Thematic clusters: {results['clusters']}")
    print(f"   Temporal chains: {results['chains']}")
    print(f"   Total links: {results['links_created']}")
