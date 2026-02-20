#!/usr/bin/env python3
"""
Test script for entity extraction comparison
"""

import sys
sys.path.insert(0, 'src')

from entity_extractor import extract_entities_regex, extract_entities_spacy

test_texts = [
    "Working with Alice on knowledge graph project using Python and Docker",
    "Anthropic released Claude 4.5 with improved reasoning capabilities",
    "Building knowledge graphs with spaCy for entity extraction in Santiago, Chile",
    "The neural network optimization project started in December 2025",
    "Integrating FastAPI with PostgreSQL database for the backend API"
]

print("=" * 80)
print("ENTITY EXTRACTION COMPARISON: Regex vs spaCy")
print("=" * 80)

for i, text in enumerate(test_texts, 1):
    print(f"\n📝 Test {i}: {text}")
    print("-" * 80)
    
    regex_entities = extract_entities_regex(text)
    print(f"\n🔧 Regex ({len(regex_entities)} entities):")
    for entity, etype in regex_entities:
        print(f"   • {entity:30} [{etype}]")
    
    spacy_entities = extract_entities_spacy(text)
    print(f"\n🧠 spaCy ({len(spacy_entities)} entities):")
    for entity, etype in spacy_entities:
        print(f"   • {entity:30} [{etype}]")
    
    # Find entities unique to each method
    regex_only = set(e[0] for e in regex_entities) - set(e[0] for e in spacy_entities)
    spacy_only = set(e[0] for e in spacy_entities) - set(e[0] for e in regex_entities)
    
    if regex_only:
        print(f"\n⚡ Regex-only: {', '.join(regex_only)}")
    if spacy_only:
        print(f"⚡ spaCy-only: {', '.join(spacy_only)}")

print("\n" + "=" * 80)
print("✅ Test completed")
print("=" * 80)
