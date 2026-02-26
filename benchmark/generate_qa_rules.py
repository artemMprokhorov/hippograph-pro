#!/usr/bin/env python3
"""
Rule-based QA generation from HippoGraph notes.
No LLM needed — uses entities extracted during ingestion + text patterns.

Strategy per note:
  1. If note has entities → "What do you know about [entity]?"
  2. If note has keywords (tech terms, dates, names) → keyword question
  3. Fallback → first sentence as question context

Output: benchmark/results/hippograph_qa.json

Usage:
  python3 benchmark/generate_qa_rules.py
  python3 benchmark/generate_qa_rules.py --min-length 30 --limit 200
"""

import json
import os
import re
import sqlite3
import argparse


DB_PATH = "data/benchmark.db"
OUT_PATH = "benchmark/results/hippograph_qa.json"


# ── Helpers ───────────────────────────────────────────────────

def extract_first_sentence(text, max_len=120):
    text = text.strip()
    for sep in [". ", ".\n", "! ", "? ", "\n"]:
        idx = text.find(sep)
        if 30 < idx < max_len:
            return text[:idx].strip()
    return text[:max_len].strip()


def detect_language(text):
    cyrillic = len(re.findall(r'[а-яА-ЯёЁ]', text))
    latin = len(re.findall(r'[a-zA-Z]', text))
    return "ru" if cyrillic > latin else "en"


def make_entity_question(entity_name, entity_type, lang):
    templates_en = {
        "person":       [f"What do you know about {entity_name}?",
                         f"Tell me about {entity_name}."],
        "organization": [f"What is {entity_name}?",
                         f"What do you know about {entity_name}?"],
        "location":     [f"What is mentioned about {entity_name}?"],
        "tech":         [f"What is {entity_name} used for?",
                         f"How is {entity_name} described?"],
        "concept":      [f"What is {entity_name}?",
                         f"Explain {entity_name}."],
        "default":      [f"What do you know about {entity_name}?"],
    }
    templates_ru = {
        "person":       [f"Что известно о {entity_name}?",
                         f"Расскажи о {entity_name}."],
        "organization": [f"Что такое {entity_name}?",
                         f"Что известно о {entity_name}?"],
        "location":     [f"Что упоминается о {entity_name}?"],
        "tech":         [f"Для чего используется {entity_name}?",
                         f"Как описывается {entity_name}?"],
        "concept":      [f"Что такое {entity_name}?",
                         f"Объясни {entity_name}."],
        "default":      [f"Что известно о {entity_name}?"],
    }
    t = (templates_ru if lang == "ru" else templates_en)
    options = t.get(entity_type, t["default"])
    return options[0]


def make_keyword_question(text, lang):
    """Extract a notable keyword/phrase and make a question."""
    # Tech terms
    tech = re.findall(
        r'\b(Docker|SQLite|FAISS|spaCy|GLiNER|BM25|MCP|API|SSH|ngrok|'
        r'HippoGraph|spreading activation|PageRank|benchmark|embedding|'
        r'LOCOMO|FastAPI|sentence.transformers|NER|HNSW)\b', text, re.I)
    if tech:
        term = tech[0]
        if lang == "ru":
            return f"Что упоминается о {term}?"
        return f"What is mentioned about {term}?"

    # Dates
    dates = re.findall(r'\b(20\d\d|January|February|March|April|May|June|July|'
                       r'August|September|October|November|December|'
                       r'января|февраля|марта|апреля|мая|июня|'
                       r'июля|августа|сентября|октября|ноября|декабря)\b', text)
    if dates:
        if lang == "ru":
            return f"Что произошло в {dates[0]}?"
        return f"What happened in {dates[0]}?"

    # Numbers / metrics
    nums = re.findall(r'\b(\d+\.?\d*\s?%|\d{3,})\b', text)
    if nums:
        if lang == "ru":
            return f"Что означает {nums[0]} в этом контексте?"
        return f"What does {nums[0]} refer to?"

    return None


def make_first_sentence_question(text, lang):
    sentence = extract_first_sentence(text)
    # Strip speaker/timestamp prefixes like "[Speaker, date]"
    sentence = re.sub(r'^\[.*?\]\s*', '', sentence).strip()
    if len(sentence) < 15:
        return None
    if lang == "ru":
        return f"Найди информацию о: {sentence[:80]}"
    return f"Find information about: {sentence[:80]}"


# ── Main generator ────────────────────────────────────────────

def generate_qa(db_path, min_length=30, limit=None):
    conn = sqlite3.connect(db_path)

    # Get notes
    q = f"SELECT id, content, category FROM nodes WHERE length(content) >= {min_length}"
    if limit:
        q += f" LIMIT {limit}"
    notes = conn.execute(q).fetchall()

    # Get entities per note
    entities_per_note = {}
    rows = conn.execute("""
        SELECT ne.node_id, e.name, e.entity_type
        FROM node_entities ne
        JOIN entities e ON ne.entity_id = e.id
    """).fetchall()
    for node_id, name, etype in rows:
        if node_id not in entities_per_note:
            entities_per_note[node_id] = []
        entities_per_note[node_id].append((name, etype))

    conn.close()

    qa_pairs = []
    skipped = 0

    for note_id, content, category in notes:
        lang = detect_language(content)
        questions = []

        # Strategy 1: entity-based questions
        ents = entities_per_note.get(note_id, [])
        # Pick top 2 most specific entities (longer name = more specific)
        ents_sorted = sorted(ents, key=lambda x: -len(x[0]))[:2]
        for name, etype in ents_sorted:
            if len(name) >= 3:
                q = make_entity_question(name, etype, lang)
                questions.append({"question": q, "category": "entity",
                                  "entity": name, "entity_type": etype})

        # Strategy 2: keyword question (if no good entities)
        if not questions:
            q = make_keyword_question(content, lang)
            if q:
                questions.append({"question": q, "category": "factual"})

        # Strategy 3: first sentence fallback
        if not questions:
            q = make_first_sentence_question(content, lang)
            if q:
                questions.append({"question": q, "category": "factual"})

        if not questions:
            skipped += 1
            continue

        for qa in questions:
            qa["note_id"] = note_id
            qa["evidence_note_ids"] = [note_id]
            qa["category"] = qa.get("category", "factual")
            qa_pairs.append(qa)

    return qa_pairs, skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument("--out", default=OUT_PATH)
    parser.add_argument("--min-length", type=int, default=30)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    print(f"📂 Loading notes from {args.db}...")
    qa_pairs, skipped = generate_qa(args.db, args.min_length, args.limit)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(qa_pairs, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated {len(qa_pairs)} QA pairs ({skipped} notes skipped)")
    print(f"💾 Saved: {args.out}")

    # Breakdown
    cats = {}
    for qa in qa_pairs:
        c = qa["category"]
        cats[c] = cats.get(c, 0) + 1
    for c, n in sorted(cats.items()):
        print(f"   {c}: {n}")

    # Sample
    print("\n📋 Sample questions:")
    for qa in qa_pairs[:5]:
        print(f"   [{qa['category']}] {qa['question']}")


if __name__ == "__main__":
    main()
