import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from opensignal.ingestion.socrata import SocrataQuery
from opensignal.ingestion.socrata_manifest import SocrataManifest
from opensignal.ingestion.socrata_runner import SocrataIngestionRunner
from opensignal.ingestion.storage import RawSnapshotStore


class FixtureSocrataClient:
    def __init__(self, fixture_dir: Path) -> None:
        self.fixture_dir = fixture_dir
        self.calls: list[int] = []

    async def fetch(self, query: SocrataQuery) -> list[dict[str, Any]]:
        self.calls.append(query.offset)
        return json.loads(
            (self.fixture_dir / f"page_{query.offset}.json").read_text(
                encoding="utf-8"
            )
        )


@pytest.mark.asyncio
async def test_socrata_ingestion_is_idempotent(tmp_path) -> None:
    fixture_dir = Path(__file__).parent / "fixtures" / "socrata"
    manifest = SocrataManifest(
        1,
        "cdc-wastewater",
        "cdc-test-snapshot",
        "data.cdc.gov",
        "j9g8-acpt",
        2,
        10,
    )
    store = RawSnapshotStore(
        tmp_path,
        manifest.snapshot_id,
        source=manifest.source,
    )

    def clock() -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC)

    first_client = FixtureSocrataClient(fixture_dir)
    first = await SocrataIngestionRunner(
        client=first_client,
        store=store,
        clock=clock,
    ).run(manifest)
    assert first.fetched_pages == 2
    assert first.total_records == 3
    assert first_client.calls == [0, 2]

    second_client = FixtureSocrataClient(fixture_dir)
    second = await SocrataIngestionRunner(
        client=second_client,
        store=store,
        clock=clock,
    ).run(manifest)
    assert second.fetched_pages == 0
    assert second.reused_pages == 2
    assert second_client.calls == []
