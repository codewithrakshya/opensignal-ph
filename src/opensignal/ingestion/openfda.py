import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

Sleep = Callable[[float], Awaitable[None]]
Clock = Callable[[], datetime]


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
    """Retry-aware asynchronous client for the openFDA drug-event endpoint."""

    retryable_statuses = frozenset({429, 500, 502, 503, 504})

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout_seconds: float = 30,
        max_attempts: int = 4,
        backoff_seconds: float = 1,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
        clock: Clock | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative")

        self.base_url = base_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.transport = transport
        self.sleep = sleep
        self.clock = clock or (lambda: datetime.now(UTC))

    async def fetch(self, query: OpenFDAQuery) -> dict[str, Any]:
        params: dict[str, str | int] = {
            "search": query.search,
            "limit": query.limit,
            "skip": query.skip,
        }
        if self.api_key:
            params["api_key"] = self.api_key

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            for attempt in range(1, self.max_attempts + 1):
                try:
                    response = await client.get(self.base_url, params=params)
                except (httpx.TimeoutException, httpx.TransportError):
                    if attempt == self.max_attempts:
                        raise
                    await self.sleep(self._backoff_delay(attempt))
                    continue

                if (
                    response.status_code in self.retryable_statuses
                    and attempt < self.max_attempts
                ):
                    await self.sleep(self._retry_delay(response, attempt))
                    continue

                response.raise_for_status()
                payload: dict[str, Any] = response.json()
                return payload

        raise RuntimeError("openFDA request ended without a response")

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0, float(retry_after))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(retry_after)
                    return max(0, (retry_at - self.clock()).total_seconds())
                except (TypeError, ValueError):
                    pass
        return self._backoff_delay(attempt)

    def _backoff_delay(self, attempt: int) -> float:
        return float(self.backoff_seconds * (2 ** (attempt - 1)))
