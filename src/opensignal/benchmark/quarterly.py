import hashlib
import json
import os
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field, HttpUrl, model_validator


class QuarterlyArchive(BaseModel):
    quarter: str = Field(pattern=r"^\d{4}Q[1-4]$")
    url: HttpUrl
    format: Literal["ascii"] = "ascii"
    posted_date: date | None = None
    approximate_size_bytes: int | None = Field(default=None, gt=0)
    expected_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    source_note: str | None = None

    @model_validator(mode="after")
    def require_official_archive(self) -> "QuarterlyArchive":
        parsed = urlparse(str(self.url))
        if parsed.scheme != "https" or parsed.hostname != "fis.fda.gov":
            raise ValueError("Quarterly archives must use HTTPS on fis.fda.gov")
        if not parsed.path.lower().endswith(".zip"):
            raise ValueError("Quarterly archive URL must point to a ZIP file")
        return self


class QuarterlyAcquisitionManifest(BaseModel):
    schema_version: int = 1
    manifest_id: str
    publisher: str = "U.S. Food and Drug Administration"
    source_page: HttpUrl
    archives: list[QuarterlyArchive]

    @model_validator(mode="after")
    def unique_quarters(self) -> "QuarterlyAcquisitionManifest":
        quarters = [archive.quarter for archive in self.archives]
        if len(quarters) != len(set(quarters)):
            raise ValueError(
                "Quarterly acquisition manifest contains duplicate quarters"
            )
        return self

    @classmethod
    def from_path(cls, path: Path) -> "QuarterlyAcquisitionManifest":
        if not path.exists():
            raise FileNotFoundError(f"Quarterly manifest not found: {path}")
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def select(self, quarters: set[str] | None = None) -> list[QuarterlyArchive]:
        if quarters is None:
            return list(self.archives)
        known = {archive.quarter for archive in self.archives}
        unknown = quarters - known
        if unknown:
            raise ValueError(f"Quarters absent from manifest: {sorted(unknown)}")
        return [
            archive for archive in self.archives if archive.quarter in quarters
        ]


class QuarterlyDownloadRecord(BaseModel):
    schema_version: int = 1
    quarter: str
    source_url: str
    retrieved_at: datetime
    bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    archive_path: str
    etag: str | None = None
    last_modified: str | None = None


class QuarterlyArchiveDownloader:
    """Stream official quarterly ZIPs and pin their observed digests."""

    def __init__(
        self,
        destination: Path,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.destination = destination
        self.client = client or httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(120.0),
        )

    def download(
        self,
        archive: QuarterlyArchive,
        *,
        max_bytes: int,
    ) -> QuarterlyDownloadRecord:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self.destination.mkdir(parents=True, exist_ok=True)
        final_path = self.destination / f"{archive.quarter}.zip"
        lock_path = self.destination / f"{archive.quarter}.lock.json"
        if final_path.exists() and lock_path.exists():
            return self._verify_existing(archive, final_path, lock_path)

        part_path = final_path.with_suffix(".zip.part")
        offset = part_path.stat().st_size if part_path.exists() else 0
        if offset > max_bytes:
            part_path.unlink()
            raise ValueError("Partial archive exceeds max_bytes")
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        digest = hashlib.sha256()
        if offset:
            with part_path.open("rb") as existing:
                for chunk in iter(lambda: existing.read(1024 * 1024), b""):
                    digest.update(chunk)

        with self.client.stream("GET", str(archive.url), headers=headers) as response:
            response.raise_for_status()
            if offset and response.status_code != httpx.codes.PARTIAL_CONTENT:
                offset = 0
                digest = hashlib.sha256()
                part_path.unlink(missing_ok=True)
            mode = "ab" if offset else "wb"
            total = offset
            with part_path.open(mode) as output:
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        output.close()
                        part_path.unlink(missing_ok=True)
                        raise ValueError(
                            f"{archive.quarter} exceeded max_bytes={max_bytes}"
                        )
                    output.write(chunk)
                    digest.update(chunk)
                output.flush()
                os.fsync(output.fileno())
            etag = response.headers.get("etag")
            last_modified = response.headers.get("last-modified")

        observed_sha256 = digest.hexdigest()
        if (
            archive.expected_sha256 is not None
            and observed_sha256 != archive.expected_sha256
        ):
            part_path.unlink(missing_ok=True)
            raise ValueError(f"SHA-256 mismatch for {archive.quarter}")
        self._validate_zip(part_path)
        os.replace(part_path, final_path)
        record = QuarterlyDownloadRecord(
            quarter=archive.quarter,
            source_url=str(archive.url),
            retrieved_at=datetime.now(UTC),
            bytes=final_path.stat().st_size,
            sha256=observed_sha256,
            archive_path=str(final_path),
            etag=etag,
            last_modified=last_modified,
        )
        self._write_json_atomically(lock_path, record.model_dump(mode="json"))
        return record

    def _verify_existing(
        self,
        archive: QuarterlyArchive,
        final_path: Path,
        lock_path: Path,
    ) -> QuarterlyDownloadRecord:
        record = QuarterlyDownloadRecord.model_validate_json(
            lock_path.read_text(encoding="utf-8")
        )
        digest = self._sha256(final_path)
        if record.quarter != archive.quarter or record.source_url != str(archive.url):
            raise ValueError(f"Archive lock provenance conflict for {archive.quarter}")
        if digest != record.sha256 or final_path.stat().st_size != record.bytes:
            raise ValueError(f"Immutable archive conflict for {archive.quarter}")
        if archive.expected_sha256 and digest != archive.expected_sha256:
            raise ValueError(f"Pinned SHA-256 mismatch for {archive.quarter}")
        self._validate_zip(final_path)
        return record

    @staticmethod
    def _validate_zip(path: Path) -> None:
        try:
            with zipfile.ZipFile(path) as archive:
                if not archive.namelist() or archive.testzip() is not None:
                    raise ValueError(f"Invalid or corrupt ZIP archive: {path}")
        except zipfile.BadZipFile as exc:
            raise ValueError(f"Invalid ZIP archive: {path}") from exc

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _write_json_atomically(path: Path, payload: dict[str, Any]) -> None:
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temp_path, path)
