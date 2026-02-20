#!/usr/bin/env python3
"""Test spaCy NER extraction"""
import sys
import os
sys.path.insert(0, 'src')

# Force spaCy mode
os.environ["ENTITY_EXTRACTOR"] = "spacy"

from entity_extractor import extract_entities_with_confidence

test_texts = [
    "Alice Johnson works at TechCorp in Berlin",
    "Apple released new iPhone in California last week",
    "The research was published in Nature on January 15th",
    "President Biden met with Angela Merkel in Berlin",
]

print("🧪 Testing spaCy NER Extraction\n")
print("=" * 70)

for i, text in enumerate(test_texts, 1):
    print(f"\n📝 Test {i}: {text}")
    entities = extract_entities_with_confidence(text)
    
    if entities:
        print(f"   Found {len(entities)} entities:")
        for entity_text, entity_type, confidence in entities:
            conf_bar = "█" * int(confidence * 10)
            print(f"   • {entity_text:25} [{entity_type:15}] {conf_bar} {confidence:.2f}")
    else:
        print("   No entities found")

print("\n" + "=" * 70)
print("✅ spaCy test complete")
