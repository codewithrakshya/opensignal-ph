import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from opensignal.ingestion import (
    IngestionManifest,
    OpenFDAIngestionRunner,
    OpenFDAQuery,
    RawSnapshotStore,
)


class FixtureClient:
    def __init__(self, fixture_dir: Path) -> None:
        self.fixture_dir = fixture_dir
        self.calls: list[int] = []

    async def fetch(self, query: OpenFDAQuery) -> dict[str, Any]:
        self.calls.append(query.skip)
        path = self.fixture_dir / f"page_{query.skip}.json"
        return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_rerun_reuses_verified_pages_without_fetching(tmp_path) -> None:
    fixtures = Path(__file__).parent / "fixtures" / "openfda"
    manifest = IngestionManifest(
        manifest_version=1,
        snapshot_id="fixture-snapshot",
        search="serious:1",
        page_size=2,
        max_records=10,
    )
    store = RawSnapshotStore(tmp_path, manifest.snapshot_id)
    first_client = FixtureClient(fixtures)

    def clock() -> datetime:
        return datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)

    first = await OpenFDAIngestionRunner(
        client=first_client,
        store=store,
        clock=clock,
    ).run(manifest)

    assert first.fetched_pages == 2
    assert first.reused_pages == 0
    assert first.total_records == 3
    assert first_client.calls == [0, 2]

    second_client = FixtureClient(fixtures)
    second = await OpenFDAIngestionRunner(
        client=second_client,
        store=store,
        clock=clock,
    ).run(manifest)

    assert second.fetched_pages == 0
    assert second.reused_pages == 2
    assert second.total_records == 3
    assert second_client.calls == []

    snapshot_files = sorted(store.snapshot_dir.glob("page-*.json"))
    assert len(snapshot_files) == 2
    checkpoint = json.loads(store.checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["completed"] is True
    assert set(checkpoint["pages"]) == {"0", "2"}


@pytest.mark.asyncio
async def test_changed_page_cannot_overwrite_snapshot(tmp_path) -> None:
    manifest = IngestionManifest(1, "immutable-snapshot", "serious:1", 2, 2)
    store = RawSnapshotStore(tmp_path, manifest.snapshot_id)
    envelope = {
        "retrieval": {"manifest_digest": manifest.digest},
        "response": {"results": [{"id": 1}]},
    }
    store.write_page(0, envelope)

    envelope["response"]["results"] = [{"id": 2}]

    with pytest.raises(FileExistsError, match="Immutable snapshot conflict"):
        store.write_page(0, envelope)
