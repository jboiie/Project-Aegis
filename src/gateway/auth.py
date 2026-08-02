"""Optional shared-key auth for the gateway — set AEGIS_API_KEY to require it."""

from fastapi import Header, HTTPException

from src.config import settings


async def verify_api_key(authorization: str | None = Header(default=None)) -> None:
    if not settings.AEGIS_API_KEY:
        return
    if authorization != f"Bearer {settings.AEGIS_API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
