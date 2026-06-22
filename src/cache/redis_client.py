"""
Redis Client — Connection management and operations.

Wraps redis.asyncio for clean async usage throughout the app.
"""

import fnmatch

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()


class MockRedis:
    """In-memory Redis substitute for development when no Redis server is available."""

    def __init__(self):
        self._data: dict = {}

    async def ping(self) -> bool:
        return True

    async def set(self, key: str, value: str, **kwargs) -> bool:
        self._data[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def scan_iter(self, match: str = "*"):
        for key in list(self._data.keys()):
            if fnmatch.fnmatch(key, match):
                yield key

    async def close(self) -> None:
        pass


class RedisCache:
    """Async Redis client with connection lifecycle management."""

    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
        self._client: aioredis.Redis | None = None

    async def connect(self):
        """Establish Redis connection pool. Falls back to in-memory mock if unavailable."""
        try:
            self._client = aioredis.Redis(
                host=self.host,
                port=self.port,
                decode_responses=True,
            )
            await self._client.ping()
            logger.info("redis_connected", host=self.host, port=self.port)
        except Exception as exc:
            logger.warning(
                "redis_unavailable",
                error=str(exc),
                action="using_in_memory_mock",
            )
            self._client = MockRedis()

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
