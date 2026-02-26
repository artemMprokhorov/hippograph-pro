#!/usr/bin/env python3
"""
Generate QA pairs from HippoGraph notes using Claude API.
Each note → 1-2 questions whose answer is contained in that note.
Output: benchmark/results/hippograph_qa.json

Usage:
  python3 benchmark/generate_qa.py --limit 100
  python3 benchmark/generate_qa.py --all
"""

import json
import os
import sqlite3
import time
import argparse
import urllib.request

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DB_PATH = "/app/data/benchmark.db"
OUT_PATH = "benchmark/results/hippograph_qa.json"
MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You generate evaluation questions for a memory retrieval system.
Given a note, generate 1-2 questions that:
1. Can ONLY be answered using information in this specific note
2. Are specific enough that only this note (not others) would answer them
3. Sound like natural queries a user would ask

Return JSON array only, no markdown:
[{"question": "...", "note_id": <id>, "category": "factual|temporal|entity"}]"""


def get_notes(db_path, limit=None):
    conn = sqlite3.connect(db_path)
    q = "SELECT id, content, category FROM nodes WHERE length(content) > 50"
    if limit:
        q += f" ORDER BY RANDOM() LIMIT {limit}"
    rows = conn.execute(q).fetchall()
    conn.close()
    return rows


def generate_qa_for_note(note_id, content, category, api_key):
    prompt = f"Note ID: {note_id}\nCategory: {category}\nContent: {content}\n\nGenerate questions:"

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 300,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            text = data["content"][0]["text"].strip()
            # Strip markdown if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            pairs = json.loads(text)
            for p in pairs:
                p["note_id"] = note_id
                p["evidence_note_ids"] = [note_id]
            return pairs
    except Exception as e:
        return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument("--out", default=OUT_PATH)
    args = parser.parse_args()

    api_key = ANTHROPIC_API_KEY
    if not api_key:
        # Try reading from .env
        env_path = "/app/.env" if os.path.exists("/app/.env") else ".env"
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith("ANTHROPIC_API_KEY="):
                    api_key = line.strip().split("=", 1)[1].strip('"').strip("'")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    limit = None if args.all else args.limit
    print(f"📂 Loading notes from {args.db}...")
    notes = get_notes(args.db, limit)
    print(f"  Notes: {len(notes)}")

    qa_pairs = []
    errors = 0

    for i, (note_id, content, category) in enumerate(notes):
        pairs = generate_qa_for_note(note_id, content, category, api_key)
        if pairs:
            qa_pairs.extend(pairs)
            print(f"  [{i+1}/{len(notes)}] note {note_id}: {len(pairs)} questions")
        else:
            errors += 1
            print(f"  [{i+1}/{len(notes)}] note {note_id}: SKIP")

        # Rate limit: ~5 req/sec for Haiku
        if i % 10 == 9:
            time.sleep(0.5)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(qa_pairs, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Generated {len(qa_pairs)} QA pairs from {len(notes)} notes ({errors} errors)")
    print(f"💾 Saved: {args.out}")

    # Category breakdown
    cats = {}
    for qa in qa_pairs:
        c = qa.get("category", "unknown")
        cats[c] = cats.get(c, 0) + 1
    for c, n in sorted(cats.items()):
        print(f"   {c}: {n}")


if __name__ == "__main__":
    main()
