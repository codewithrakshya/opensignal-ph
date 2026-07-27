from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Protocol

from opensignal.ingestion.runner import IngestionResult
from opensignal.ingestion.socrata import SocrataQuery
from opensignal.ingestion.socrata_manifest import SocrataManifest
from opensignal.ingestion.storage import Checkpoint, RawSnapshotStore


class SocrataPageFetcher(Protocol):
    async def fetch(self, query: SocrataQuery) -> list[dict[str, Any]]: ...


class SocrataIngestionRunner:
    def __init__(
        self,
        *,
        client: SocrataPageFetcher,
        store: RawSnapshotStore,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.client = client
        self.store = store
        self.clock = clock or (lambda: datetime.now(UTC))

    async def run(self, manifest: SocrataManifest) -> IngestionResult:
        checkpoint = Checkpoint.load_or_create(
            self.store.checkpoint_path,
            manifest_digest=manifest.digest,
            snapshot_id=manifest.snapshot_id,
        )
        fetched_pages = 0
        reused_pages = 0
        total_records = 0

        for offset in range(0, manifest.max_records, manifest.page_size):
            existing = checkpoint.pages.get(str(offset))
            if existing and self.store.verify_page(existing):
                reused_pages += 1
                total_records += existing.records
                if existing.records < manifest.page_size:
                    break
                continue

            limit = min(manifest.page_size, manifest.max_records - offset)
            query = SocrataQuery(
                limit=limit,
                offset=offset,
                where=manifest.where,
                order=manifest.order,
                select=manifest.select,
            )
            results = await self.client.fetch(query)
            envelope = {
                "retrieval": {
                    "retrieved_at": self.clock().isoformat(),
                    "manifest": asdict(manifest),
                    "manifest_digest": manifest.digest,
                    "request": asdict(query),
                },
                "response": {"results": results},
            }
            page = self.store.write_page(offset, envelope)
            checkpoint.pages[str(offset)] = page
            checkpoint.save(self.store.checkpoint_path)
            fetched_pages += 1
            total_records += page.records
            if page.records < limit:
                break

        checkpoint.completed = True
        checkpoint.save(self.store.checkpoint_path)
        return IngestionResult(
            snapshot_id=manifest.snapshot_id,
            fetched_pages=fetched_pages,
            reused_pages=reused_pages,
            total_records=total_records,
            completed=True,
        )
