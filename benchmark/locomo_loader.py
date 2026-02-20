#!/usr/bin/env python3
"""
LOCOMO Loader — loads benchmark sessions into HippoGraph DB.
Run INSIDE Docker container: docker exec hippograph-bench python3 /app/benchmark/locomo_loader.py
"""
import json
import sys
import time
import os

sys.path.insert(0, "/app/src")

from database import get_connection, init_database
from graph_engine import add_note_with_links

LOCOMO_DATA = "/app/benchmark/locomo10.json"

def load_sessions():
    init_database()
    
    with open(LOCOMO_DATA) as f:
        data = json.load(f)
    
    total = 0
    session_map = {}
    
    for conv_idx, item in enumerate(data):
        conv = item["conversation"]
        sa = conv.get("speaker_a", f"A{conv_idx}")
        sb = conv.get("speaker_b", f"B{conv_idx}")
        
        sn = 1
        while f"session_{sn}" in conv:
            turns = conv[f"session_{sn}"]
            ts = conv.get(f"session_{sn}_date_time", "")
            
            lines = [f"[{sa} & {sb} — {ts}]"]
            dia_ids = []
            
            for t in turns:
                text = t.get("text", "")
                spk = t.get("speaker", "?")
                did = t.get("dia_id", "")
                if text:
                    lines.append(f"{spk}: {text}")
                if did:
                    dia_ids.append(did)
            
            content = "\n".join(lines)
            cat = f"locomo-conv{conv_idx}"
            
            try:
                result = add_note_with_links(content, category=cat)
                nid = result.get("id") if isinstance(result, dict) else result
                session_map[str(nid)] = {
                    "dia_ids": dia_ids,
                    "conv_id": conv_idx,
                    "session_num": sn
                }
                total += 1
            except Exception as e:
                print(f"  ERR c{conv_idx} s{sn}: {e}")
            
            sn += 1
        
        print(f"  Conv {conv_idx} ({sa} & {sb}): {sn-1} sessions")
    
    mp = "/app/benchmark/session_dia_map.json"
    with open(mp, "w") as f:
        json.dump(session_map, f)
    
    print(f"\nTotal: {total} notes")
    print(f"Map: {mp}")

if __name__ == "__main__":
    t0 = time.time()
    load_sessions()
    print(f"Done in {time.time()-t0:.1f}s")
