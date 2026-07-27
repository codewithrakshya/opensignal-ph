from collections.abc import Awaitable

import httpx
import pytest

from opensignal.ingestion.openfda import OpenFDAClient, OpenFDAQuery


@pytest.mark.asyncio
async def test_client_retries_rate_limit_and_honors_retry_after() -> None:
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0.25"})
        return httpx.Response(200, json={"results": [{"id": "ok"}]})

    def sleep(delay: float) -> Awaitable[None]:
        delays.append(delay)

        async def complete() -> None:
            return None

        return complete()

    client = OpenFDAClient(
        "https://api.fda.gov/drug/event.json",
        max_attempts=2,
        transport=httpx.MockTransport(handler),
        sleep=sleep,
    )

    response = await client.fetch(OpenFDAQuery(search="serious:1"))

    assert response["results"] == [{"id": "ok"}]
    assert attempts == 2
    assert delays == [0.25]


def test_query_enforces_openfda_page_limit() -> None:
    with pytest.raises(ValueError, match="between 1 and 1000"):
        OpenFDAQuery(search="serious:1", limit=1_001)
