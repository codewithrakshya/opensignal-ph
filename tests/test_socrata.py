from collections.abc import Awaitable

import httpx
import pytest

from opensignal.ingestion.socrata import SocrataClient, SocrataQuery


@pytest.mark.asyncio
async def test_socrata_client_builds_query_and_retries() -> None:
    requests: list[httpx.Request] = []
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=[{"record_id": "ok"}])

    def sleep(delay: float) -> Awaitable[None]:
        delays.append(delay)

        async def complete() -> None:
            return None

        return complete()

    client = SocrataClient(
        "data.cdc.gov",
        "j9g8-acpt",
        app_token="test-token",
        max_attempts=2,
        backoff_seconds=0.5,
        transport=httpx.MockTransport(handler),
        sleep=sleep,
    )
    response = await client.fetch(
        SocrataQuery(
            limit=100,
            offset=200,
            where="sample_collect_date >= '2026-01-01'",
            order="sample_collect_date,record_id",
        )
    )

    assert response == [{"record_id": "ok"}]
    assert delays == [0.5]
    assert requests[-1].headers["X-App-Token"] == "test-token"
    query = dict(requests[-1].url.params)
    assert query["$limit"] == "100"
    assert query["$offset"] == "200"
    assert query["$order"] == "sample_collect_date,record_id"


@pytest.mark.asyncio
async def test_socrata_client_rejects_non_list_response() -> None:
    client = SocrataClient(
        "data.cdc.gov",
        "j9g8-acpt",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"not": "a list"})
        ),
    )

    with pytest.raises(ValueError, match="list of objects"):
        await client.fetch(SocrataQuery(limit=1, offset=0))
