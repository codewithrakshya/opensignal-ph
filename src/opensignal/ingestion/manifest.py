import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")


@dataclass(frozen=True)
class IngestionManifest:
    """A versioned, bounded request for an openFDA raw-data snapshot."""

    manifest_version: int
    snapshot_id: str
    search: str
    page_size: int
    max_records: int

    def __post_init__(self) -> None:
        if self.manifest_version != 1:
            raise ValueError("Only manifest_version 1 is supported")
        if not SAFE_ID.fullmatch(self.snapshot_id):
            raise ValueError(
                "snapshot_id must be 3-64 lowercase letters, numbers, _ or -"
            )
        if not self.search.strip():
            raise ValueError("search cannot be empty")
        if not 1 <= self.page_size <= 1_000:
            raise ValueError("page_size must be between 1 and 1000")
        if not 1 <= self.max_records <= 25_000:
            raise ValueError("max_records must be between 1 and 25000")

    @classmethod
    def from_path(cls, path: Path) -> "IngestionManifest":
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        expected = {
            "manifest_version",
            "snapshot_id",
            "search",
            "page_size",
            "max_records",
        }
        unknown = set(payload) - expected
        missing = expected - set(payload)
        if unknown:
            raise ValueError(f"Unknown manifest fields: {sorted(unknown)}")
        if missing:
            raise ValueError(f"Missing manifest fields: {sorted(missing)}")
        return cls(**payload)

    @property
    def digest(self) -> str:
        canonical = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(canonical).hexdigest()
