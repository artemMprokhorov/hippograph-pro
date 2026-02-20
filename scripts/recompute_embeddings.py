#!/usr/bin/env python3
"""
Recompute embeddings for all notes.
Use this if embedding model changed or embeddings are corrupted.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import get_all_nodes, update_node
from stable_embeddings import get_model


def recompute_all():
    print("🔄 Recomputing embeddings for all notes...")
    
    model = get_model()
    nodes = get_all_nodes()
    
    print(f"   Found {len(nodes)} notes")
    
    for i, node in enumerate(nodes):
        content = node["content"]
        embedding = model.encode(content)[0]
        update_node(node["id"], embedding=embedding.tobytes())
        
        if (i + 1) % 10 == 0:
            print(f"   Processed {i + 1}/{len(nodes)}")
    
    print(f"✅ Done! Recomputed {len(nodes)} embeddings")


if __name__ == "__main__":
    recompute_all()
