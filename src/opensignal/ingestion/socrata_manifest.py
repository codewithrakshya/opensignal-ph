import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from opensignal.ingestion.manifest import SAFE_ID

DATASET_ID = re.compile(r"^[a-z0-9]{4}-[a-z0-9]{4}$")
DOMAIN = re.compile(r"^[a-z0-9.-]+\.[a-z]{2,}$")


@dataclass(frozen=True)
class SocrataManifest:
    """A bounded, versioned request for one Socrata dataset snapshot."""

    manifest_version: int
    source: str
    snapshot_id: str
    domain: str
    dataset_id: str
    page_size: int
    max_records: int
    where: str | None = None
    order: str = ":id"
    select: str | None = None

    def __post_init__(self) -> None:
        if self.manifest_version != 1:
            raise ValueError("Only manifest_version 1 is supported")
        if not SAFE_ID.fullmatch(self.source):
            raise ValueError("source must be a safe lowercase identifier")
        if not SAFE_ID.fullmatch(self.snapshot_id):
            raise ValueError("snapshot_id must be a safe lowercase identifier")
        if not DOMAIN.fullmatch(self.domain):
            raise ValueError("domain must be a hostname")
        if not DATASET_ID.fullmatch(self.dataset_id):
            raise ValueError("dataset_id must use the Socrata xxxx-xxxx format")
        if not 1 <= self.page_size <= 50_000:
            raise ValueError("page_size must be between 1 and 50000")
        if not 1 <= self.max_records <= 250_000:
            raise ValueError("max_records must be between 1 and 250000")
        if not self.order.strip():
            raise ValueError("order cannot be blank")

    @classmethod
    def from_path(cls, path: Path) -> "SocrataManifest":
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        expected = {
            "manifest_version",
            "source",
            "snapshot_id",
            "domain",
            "dataset_id",
            "page_size",
            "max_records",
            "where",
            "order",
            "select",
        }
        unknown = set(payload) - expected
        required = expected - {"where", "order", "select"}
        missing = required - set(payload)
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
