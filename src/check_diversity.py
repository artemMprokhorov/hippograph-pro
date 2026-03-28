#!/usr/bin/env python3
import requests
import json
import numpy as np
import os

API_KEY = os.getenv("NEURAL_API_KEY", "change_me_in_production") 
API_URL = f"http://172.17.0.2:5000/api/search?api_key={API_KEY}" # Use container IP and internal port
HEADERS = {"Content-Type": "application/json"} # X-API-Key removed, using URL param

TEST_SAMPLES = [
    ("Who is Artem?", 4), # Prod ID
    ("What happened to Ollama?", 136), # Prod ID
    ("Why was GLiNER chosen?", 675), # Prod ID
    ("Who created the logo for HippoGraph?", 190), # Prod ID
    ("What is the Phi-proxy metric?", 900), # Prod ID
    ("What are the indicators of consciousness?", 47), # Prod ID
    ("Recall@5 results for LOCOMO", 193), # Prod ID
    ("critical lesson regarding confabulation", 296), # Prod ID
]

def run_bench(label):
    print(f"Running Recall@5 test on {API_URL} (Production - Variant 2)...")
    hits = 0
    communities = []
    
    for query, target_id in TEST_SAMPLES:
        try:
            r = requests.post(API_URL, json={"query": query, "limit": 10}, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", []) if isinstance(data, dict) else data
                node_ids_in_top5 = [res.get("id") or res.get("node_id") for res in results[:5]]
                if target_id in node_ids_in_top5: 
                    hits += 1
                    print(f"  HIT: {query[:40]}...")
                else:
                    print(f"  MISS: {query[:40]}... (Found: {node_ids_in_top5})")
                
                cats = set(res.get("category") for res in results)
                communities.append(len(cats))
            else:
                print(f"  ERR: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"  FAIL: {e}")
            
    # Corrected variable name for recall calculation
    recall = hits / len(TEST_SAMPLES) 
    avg_div = np.mean(communities) if communities else 0
    print(f"\nFINAL RECALL@5: {recall:.1%}")
    print(f"DIVERSITY (Avg Categories in Top-10): {avg_div:.2f}")
    return recall, avg_div

if __name__ == "__main__":
    import sys
    run_bench(sys.argv[1] if len(sys.argv) > 1 else "Unknown")