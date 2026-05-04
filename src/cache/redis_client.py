"""
Redis Client — Connection management and operations.

Wraps redis.asyncio for clean async usage throughout the app.
"""

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()


class RedisCache:
    """Async Redis client with connection lifecycle management."""

    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
        self._client: aioredis.Redis | None = None

    async def connect(self):
        """Establish Redis connection pool."""
        self._client = aioredis.Redis(
            host=self.host,
            port=self.port,
            decode_responses=True,
        )
        await self._client.ping()
        logger.info("redis_connected", host=self.host, port=self.port)

    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            logger.info("redis_disconnected")

    @property
    def client(self) -> aioredis.Redis:
        if self._client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client
