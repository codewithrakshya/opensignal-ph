import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from opensignal.ingestion.manifest import SAFE_ID


def canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


@dataclass(frozen=True)
class PageRecord:
    skip: int
    records: int
    path: str
    sha256: str


@dataclass
class Checkpoint:
    manifest_digest: str
    snapshot_id: str
    pages: dict[str, PageRecord] = field(default_factory=dict)
    completed: bool = False

    @classmethod
    def load_or_create(
        cls,
        path: Path,
        *,
        manifest_digest: str,
        snapshot_id: str,
    ) -> "Checkpoint":
        if not path.exists():
            return cls(
                manifest_digest=manifest_digest,
                snapshot_id=snapshot_id,
            )
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        if payload["manifest_digest"] != manifest_digest:
            raise ValueError("Checkpoint manifest digest does not match")
        pages = {
            key: PageRecord(**value)
            for key, value in payload.get("pages", {}).items()
        }
        return cls(
            manifest_digest=payload["manifest_digest"],
            snapshot_id=payload["snapshot_id"],
            pages=pages,
            completed=payload.get("completed", False),
        )

    def save(self, path: Path) -> None:
        payload = {
            "manifest_digest": self.manifest_digest,
            "snapshot_id": self.snapshot_id,
            "pages": {
                key: asdict(value)
                for key, value in sorted(
                    self.pages.items(),
                    key=lambda item: int(item[0]),
                )
            },
            "completed": self.completed,
        }
        atomic_write(path, canonical_json_bytes(payload))


class RawSnapshotStore:
    """Writes content-addressed immutable page envelopes."""

    def __init__(
        self,
        data_dir: Path,
        snapshot_id: str,
        *,
        source: str = "openfda",
    ) -> None:
        if not SAFE_ID.fullmatch(source):
            raise ValueError("source must be a safe lowercase identifier")
        self.data_dir = data_dir
        self.snapshot_id = snapshot_id
        self.source = source
        self.snapshot_dir = data_dir / "raw" / source / snapshot_id
        self.checkpoint_path = (
            data_dir / "checkpoints" / source / f"{snapshot_id}.json"
        )

    def page_path(self, skip: int) -> Path:
        return self.snapshot_dir / f"page-{skip:09d}.json"

    def write_page(self, skip: int, envelope: dict[str, Any]) -> PageRecord:
        content = canonical_json_bytes(envelope)
        digest = sha256_bytes(content)
        path = self.page_path(skip)

        if path.exists():
            existing = path.read_bytes()
            if sha256_bytes(existing) != digest:
                raise FileExistsError(
                    f"Immutable snapshot conflict at {path}; use a new snapshot_id"
                )
        else:
            atomic_write(path, content)

        return PageRecord(
            skip=skip,
            records=len(envelope["response"]["results"]),
            path=str(path.relative_to(self.data_dir)),
            sha256=digest,
        )

    def verify_page(self, page: PageRecord) -> bool:
        path = self.data_dir / page.path
        return path.exists() and sha256_bytes(path.read_bytes()) == page.sha256
