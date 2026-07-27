from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class OpenFDAQuery:
    search: str
    limit: int = 100
    skip: int = 0

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= 1_000:
            raise ValueError("openFDA limit must be between 1 and 1000")
        if self.skip < 0:
            raise ValueError("openFDA skip cannot be negative")


class OpenFDAClient:
    """Small source adapter; persistence and checkpoints arrive in Phase 1."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout_seconds: float = 30,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def fetch(self, query: OpenFDAQuery) -> dict[str, Any]:
        params: dict[str, str | int] = {
            "search": query.search,
            "limit": query.limit,
            "skip": query.skip,
        }
        if self.api_key:
            params["api_key"] = self.api_key

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            return payload
