#!/usr/bin/env python3
"""
BM25 Keyword Search for Neural Memory Graph.
Builds inverted index at startup, provides keyword scoring for blend search.
Zero external dependencies — pure Python + math.
"""
import math
import re
import os
import time
from typing import Dict, List, Tuple
from collections import Counter

# BM25 parameters (standard defaults)
BM25_K1 = float(os.getenv("BM25_K1", "1.5"))  # term frequency saturation
BM25_B = float(os.getenv("BM25_B", "0.75"))     # length normalization


def tokenize(text: str) -> List[str]:
    """Simple whitespace + punctuation tokenizer, lowercased."""
    return re.findall(r'[a-zA-Zа-яА-ЯёЁ0-9_]+', text.lower())


class BM25Index:
    """Okapi BM25 inverted index for keyword search."""
    
    def __init__(self):
        self._doc_freqs: Dict[str, int] = {}      # term → num docs containing it
        self._doc_lens: Dict[int, int] = {}        # node_id → doc length
        self._doc_terms: Dict[int, Counter] = {}   # node_id → term frequencies
        self._avg_dl: float = 0.0                  # average document length
        self._n_docs: int = 0
        self._node_ids: List[int] = []
        self._built: bool = False
    
    def build(self, documents: List[Tuple[int, str]]):
        """
        Build index from list of (node_id, content) pairs.
        Called once at startup.
        """
        start = time.time()
        
        self._doc_freqs = {}
        self._doc_lens = {}
        self._doc_terms = {}
        self._node_ids = []
        
        total_len = 0
        
        for node_id, content in documents:
            tokens = tokenize(content)
            tf = Counter(tokens)
            
            self._doc_terms[node_id] = tf
            self._doc_lens[node_id] = len(tokens)
            self._node_ids.append(node_id)
            total_len += len(tokens)
            
            # Update document frequencies
            for term in tf:
                self._doc_freqs[term] = self._doc_freqs.get(term, 0) + 1
        
        self._n_docs = len(documents)
        self._avg_dl = total_len / max(self._n_docs, 1)
        self._built = True
        
        elapsed = time.time() - start
        print(f"🔍 BM25 index built in {elapsed:.2f}s: "
              f"{self._n_docs} docs, {len(self._doc_freqs)} unique terms, "
              f"avg_dl={self._avg_dl:.1f}")
    
    def add_document(self, node_id: int, content: str):
        """Add a single document to the index (for new notes)."""
        tokens = tokenize(content)
        tf = Counter(tokens)
        
        self._doc_terms[node_id] = tf
        self._doc_lens[node_id] = len(tokens)
        if node_id not in self._node_ids:
            self._node_ids.append(node_id)
        
        # Update stats
        total_len = sum(self._doc_lens.values())
        self._n_docs = len(self._doc_terms)
        self._avg_dl = total_len / max(self._n_docs, 1)
        
        for term in tf:
            self._doc_freqs[term] = self._doc_freqs.get(term, 0) + 1
    
    def search(self, query: str, top_k: int = 50) -> Dict[int, float]:
        """
        Score all documents against query using BM25.
        Returns dict of {node_id: bm25_score} for top_k results.
        """
        if not self._built:
            return {}
        
        query_tokens = tokenize(query)
        if not query_tokens:
            return {}
        
        scores: Dict[int, float] = {}
        
        for node_id in self._node_ids:
            score = 0.0
            tf = self._doc_terms.get(node_id, {})
            dl = self._doc_lens.get(node_id, 0)
            
            for term in query_tokens:
                if term not in tf:
                    continue
                
                # IDF: log((N - df + 0.5) / (df + 0.5) + 1)
                df = self._doc_freqs.get(term, 0)
                idf = math.log((self._n_docs - df + 0.5) / (df + 0.5) + 1.0)
                
                # TF component with length normalization
                freq = tf[term]
                tf_norm = (freq * (BM25_K1 + 1)) / (
                    freq + BM25_K1 * (1 - BM25_B + BM25_B * dl / self._avg_dl)
                )
                
                score += idf * tf_norm
            
            if score > 0:
                scores[node_id] = score
        
        # Return top-k
        if len(scores) > top_k:
            sorted_scores = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
            return dict(sorted_scores)
        
        return scores
    
    @property
    def is_built(self) -> bool:
        return self._built
    
    @property
    def vocab_size(self) -> int:
        return len(self._doc_freqs)


# Singleton
_bm25 = BM25Index()


def get_bm25_index() -> BM25Index:
    return _bm25
