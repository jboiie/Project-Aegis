"""
Embedding Model — Shared embedding utility for semantic cache.

Uses all-MiniLM-L6-v2 (22MB, 384-dim embeddings) for:
  - Semantic cache similarity matching
  - Prompt clustering in telemetry
  - Attack diversity measurement in red-teaming

This model runs on CPU with ~3ms per embedding. No GPU required.
"""

import numpy as np


class EmbeddingModel:
    """Wrapper around sentence-transformers for generating text embeddings."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def load(self):
        """Load the embedding model into memory."""
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self.model_name)

    def encode(self, text: str) -> np.ndarray:
        """
        Generate an embedding vector for the given text.

        Args:
            text: Input text to embed.

        Returns:
            384-dimensional numpy array.
        """
        if self._model is None:
            self.load()
        return self._model.encode(text, convert_to_numpy=True)

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for a batch of texts."""
        if self._model is None:
            self.load()
        return self._model.encode(texts, convert_to_numpy=True, batch_size=32)
