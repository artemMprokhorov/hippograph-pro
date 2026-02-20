#!/usr/bin/env python3
"""Test enhanced entity extraction"""
import sys
sys.path.insert(0, 'src')

from entity_extractor import extract_entities_with_confidence

# Test cases
test_texts = [
    "Claude and Artem are working on FAISS indexing with Docker",
    "The neural network uses PyTorch transformers for embeddings",
    "GitHub repository uses Python, TypeScript, and PostgreSQL",
    "Spreading activation in memory graph finds semantic connections",
]

print("🧪 Testing Enhanced Entity Extraction\n")
print("=" * 70)

for i, text in enumerate(test_texts, 1):
    print(f"\n📝 Test {i}: {text[:60]}...")
    entities = extract_entities_with_confidence(text)
    
    if entities:
        print(f"   Found {len(entities)} entities:")
        for entity_text, entity_type, confidence in entities:
            conf_bar = "█" * int(confidence * 10)
            print(f"   • {entity_text:20} [{entity_type:15}] {conf_bar} {confidence:.2f}")
    else:
        print("   No entities found")

print("\n" + "=" * 70)
print("✅ Test complete")
