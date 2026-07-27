import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx

Sleep = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class SocrataQuery:
    limit: int
    offset: int
    where: str | None = None
    order: str = ":id"
    select: str | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= 50_000:
            raise ValueError("Socrata limit must be between 1 and 50000")
        if self.offset < 0:
            raise ValueError("Socrata offset cannot be negative")


class SocrataClient:
    """Retry-aware client for Socrata Open Data API endpoints."""

    retryable_statuses = frozenset({429, 500, 502, 503, 504})

    def __init__(
        self,
        domain: str,
        dataset_id: str,
        *,
        app_token: str | None = None,
        timeout_seconds: float = 30,
        max_attempts: int = 4,
        backoff_seconds: float = 1,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative")
        self.url = f"https://{domain}/resource/{dataset_id}.json"
        self.app_token = app_token
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.transport = transport
        self.sleep = sleep

    async def fetch(self, query: SocrataQuery) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {
            "$limit": query.limit,
            "$offset": query.offset,
            "$order": query.order,
        }
        if query.where:
            params["$where"] = query.where
        if query.select:
            params["$select"] = query.select
        headers = {"X-App-Token": self.app_token} if self.app_token else None

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            for attempt in range(1, self.max_attempts + 1):
                try:
                    response = await client.get(
                        self.url,
                        params=params,
                        headers=headers,
                    )
                except (httpx.TimeoutException, httpx.TransportError):
                    if attempt == self.max_attempts:
                        raise
                    await self.sleep(self._backoff_delay(attempt))
                    continue

                if (
                    response.status_code in self.retryable_statuses
                    and attempt < self.max_attempts
                ):
                    retry_after = response.headers.get("Retry-After")
                    delay = (
                        float(retry_after)
                        if retry_after and retry_after.replace(".", "", 1).isdigit()
                        else self._backoff_delay(attempt)
                    )
                    await self.sleep(delay)
                    continue

                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list) or not all(
                    isinstance(item, dict) for item in payload
                ):
                    raise ValueError("Socrata response must be a list of objects")
                return payload

        raise RuntimeError("Socrata request ended without a response")

    def _backoff_delay(self, attempt: int) -> float:
        return float(self.backoff_seconds * (2 ** (attempt - 1)))
