from typing import Protocol

from opensignal.quality.processor import ProcessingResult


class SnapshotProcessor(Protocol):
    """Source-neutral contract for validation and curation adapters."""

    source: str

    def process(self, snapshot_id: str) -> ProcessingResult: ...
