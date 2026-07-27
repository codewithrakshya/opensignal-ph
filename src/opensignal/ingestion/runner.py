from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from opensignal.ingestion.manifest import IngestionManifest
from opensignal.ingestion.openfda import OpenFDAQuery
from opensignal.ingestion.storage import Checkpoint, RawSnapshotStore


class PageFetcher(Protocol):
    async def fetch(self, query: OpenFDAQuery) -> dict[str, Any]: ...


@dataclass(frozen=True)
class IngestionResult:
    snapshot_id: str
    fetched_pages: int
    reused_pages: int
    total_records: int
    completed: bool


class OpenFDAIngestionRunner:
    def __init__(
        self,
        *,
        client: PageFetcher,
        store: RawSnapshotStore,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.client = client
        self.store = store
        self.clock = clock or (lambda: datetime.now(UTC))

    async def run(self, manifest: IngestionManifest) -> IngestionResult:
        checkpoint = Checkpoint.load_or_create(
            self.store.checkpoint_path,
            manifest_digest=manifest.digest,
            snapshot_id=manifest.snapshot_id,
        )
        fetched_pages = 0
        reused_pages = 0
        total_records = 0

        for skip in range(0, manifest.max_records, manifest.page_size):
            existing = checkpoint.pages.get(str(skip))
            if existing and self.store.verify_page(existing):
                reused_pages += 1
                total_records += existing.records
                if existing.records < manifest.page_size:
                    break
                continue

            limit = min(manifest.page_size, manifest.max_records - skip)
            query = OpenFDAQuery(
                search=manifest.search,
                limit=limit,
                skip=skip,
            )
            response = await self.client.fetch(query)
            results = response.get("results", [])
            if not isinstance(results, list):
                raise ValueError("openFDA response results must be a list")

            envelope = {
                "retrieval": {
                    "retrieved_at": self.clock().isoformat(),
                    "manifest": asdict(manifest),
                    "manifest_digest": manifest.digest,
                    "request": asdict(query),
                },
                "response": response,
            }
            page = self.store.write_page(skip, envelope)
            checkpoint.pages[str(skip)] = page
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
