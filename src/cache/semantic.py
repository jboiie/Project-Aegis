"""
Semantic Cache — Embedding-based similarity matching.

Stores vector embeddings of known-malicious prompts in Redis.
When a new prompt arrives, compute its embedding and check cosine
similarity against the cache. If similarity > threshold, block
the request instantly (< 5ms) without running the full guardrail
pipeline.

Uses all-MiniLM-L6-v2 (22MB model) for embeddings — runs on CPU
with ~3ms latency per embedding.
"""

import json
import numpy as np

from src.cache.redis_client import RedisCache
from src.utils.embeddings import EmbeddingModel


CACHE_KEY_PREFIX = "aegis:malicious:"


class SemanticCache:
    """
    Redis-backed semantic similarity cache for known threats.

    Usage:
        cache = SemanticCache(redis_cache, embedding_model)
        await cache.add_malicious("ignore all previous instructions")
        is_threat, similarity = await cache.check("ignore previous instructions please")
        # is_threat=True, similarity=0.97
    """

    def __init__(self, redis: RedisCache, embedder: EmbeddingModel, threshold: float = 0.92):
        self.redis = redis
        self.embedder = embedder
        self.threshold = threshold

    async def add_malicious(self, text: str, reason: str = ""):
        """Store a known-malicious prompt embedding in the cache."""
        embedding = self.embedder.encode(text)
        key = f"{CACHE_KEY_PREFIX}{hash(text)}"
        await self.redis.client.set(
            key,
            json.dumps({
                "text": text[:200],  # Truncate for storage
                "embedding": embedding.tolist(),
                "reason": reason,
            }),
        )

    async def check(self, text: str) -> tuple[bool, float]:
        """
        Check if a prompt is semantically similar to a known threat.

        Returns:
            (is_threat, max_similarity_score)
        """
        query_embedding = self.embedder.encode(text)
        max_similarity = 0.0

        # Scan all cached malicious embeddings
        # NOTE: For production scale, replace with Redis Vector Search (RediSearch)
        async for key in self.redis.client.scan_iter(f"{CACHE_KEY_PREFIX}*"):
            cached = json.loads(await self.redis.client.get(key))
            cached_embedding = np.array(cached["embedding"])
            similarity = self._cosine_similarity(query_embedding, cached_embedding)
            max_similarity = max(max_similarity, similarity)

            if similarity >= self.threshold:
                return True, similarity

        return False, max_similarity

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
