import hashlib
import io
import json
import zipfile
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from opensignal.benchmark.quarterly import (
    QuarterlyAcquisitionManifest,
    QuarterlyArchive,
    QuarterlyArchiveDownloader,
)


def zip_payload() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("ASCII/DEMO24Q1.txt", "primaryid$caseid\n1$1\n")
    return buffer.getvalue()


def test_checked_in_manifest_selects_explicit_quarters() -> None:
    manifest = QuarterlyAcquisitionManifest.from_path(
        Path("manifests/faers-quarterly-2024-2025.json")
    )
    assert len(manifest.archives) == 8
    assert [item.quarter for item in manifest.select({"2024Q1", "2025Q4"})] == [
        "2024Q1",
        "2025Q4",
    ]
    with pytest.raises(ValueError, match="absent"):
        manifest.select({"2023Q4"})


def test_archive_rejects_non_fda_host() -> None:
    with pytest.raises(ValidationError, match="fis.fda.gov"):
        QuarterlyArchive(
            quarter="2024Q1",
            url="https://example.com/faers_ascii_2024q1.zip",
        )


def test_download_pins_digest_and_reuses_verified_archive(tmp_path: Path) -> None:
    payload = zip_payload()
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            content=payload,
            headers={"etag": '"demo-etag"'},
            request=request,
        )

    archive = QuarterlyArchive(
        quarter="2024Q1",
        url="https://fis.fda.gov/content/Exports/faers_ascii_2024q1.zip",
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))
    downloader = QuarterlyArchiveDownloader(tmp_path, client=client)
    first = downloader.download(archive, max_bytes=1_000_000)
    second = downloader.download(archive, max_bytes=1_000_000)

    assert calls == 1
    assert first == second
    assert first.sha256 == hashlib.sha256(payload).hexdigest()
    assert json.loads((tmp_path / "2024Q1.lock.json").read_text())["etag"] == (
        '"demo-etag"'
    )


def test_download_fails_closed_when_archive_exceeds_limit(tmp_path: Path) -> None:
    payload = zip_payload()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload, request=request)

    archive = QuarterlyArchive(
        quarter="2024Q1",
        url="https://fis.fda.gov/content/Exports/faers_ascii_2024q1.zip",
    )
    downloader = QuarterlyArchiveDownloader(
        tmp_path,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(ValueError, match="exceeded"):
        downloader.download(archive, max_bytes=10)
    assert not (tmp_path / "2024Q1.zip").exists()
    assert not (tmp_path / "2024Q1.zip.part").exists()


def test_existing_archive_conflict_fails_closed(tmp_path: Path) -> None:
    payload = zip_payload()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload, request=request)

    archive = QuarterlyArchive(
        quarter="2024Q1",
        url="https://fis.fda.gov/content/Exports/faers_ascii_2024q1.zip",
    )
    downloader = QuarterlyArchiveDownloader(
        tmp_path,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    downloader.download(archive, max_bytes=1_000_000)
    (tmp_path / "2024Q1.zip").write_bytes(b"changed")
    with pytest.raises(ValueError, match="Immutable archive conflict"):
        downloader.download(archive, max_bytes=1_000_000)
