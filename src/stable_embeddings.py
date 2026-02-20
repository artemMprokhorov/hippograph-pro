#!/usr/bin/env python3
"""
Stable Embeddings using HuggingFace Transformers
Direct implementation for consistent embeddings across rebuilds
"""

import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from typing import List, Union
import os


class StableEmbeddingModel:
    """Direct transformers implementation for stable embeddings"""
    
    def __init__(self, model_name: str = None):
        model_name = model_name or os.getenv(
            "EMBEDDING_MODEL", 
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        
        print(f"🤖 Loading embedding model: {model_name}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)
            self.model.eval()
            
            self.device = torch.device("cpu")
            self.model.to(self.device)
            
            print(f"✅ Model loaded on {self.device}")
            
        except Exception as e:
            print(f"❌ Model loading failed: {e}")
            raise

    
    def encode(self, sentences: Union[str, List[str]]) -> np.ndarray:
        """Encode sentences to embeddings"""
        if isinstance(sentences, str):
            sentences = [sentences]
        
        try:
            inputs = self.tokenizer(
                sentences,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            embeddings = self._mean_pooling(
                outputs.last_hidden_state, 
                inputs["attention_mask"]
            )
            
            return embeddings.cpu().numpy()
            
        except Exception as e:
            print(f"❌ Encoding failed: {e}")
            raise
    
    def _mean_pooling(self, embeddings: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """Mean pooling with attention mask"""
        mask_expanded = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
        sum_embeddings = torch.sum(embeddings * mask_expanded, dim=1)
        sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
        return sum_embeddings / sum_mask

    @property
    def dimension(self) -> int:
        """Return embedding dimension from model config."""
        return self.model.config.hidden_size


# Singleton for lazy loading
_model = None

def get_model():
    """Get or create embedding model singleton"""
    global _model
    if _model is None:
        _model = StableEmbeddingModel()
    return _model


if __name__ == "__main__":
    # Test embedding
    model = StableEmbeddingModel()
    emb = model.encode(["Test sentence for embedding"])
    print(f"Embedding shape: {emb.shape}")
    print(f"First 5 values: {emb[0][:5]}")
