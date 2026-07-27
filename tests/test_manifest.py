import json

import pytest

from opensignal.ingestion.manifest import IngestionManifest


def test_manifest_is_strict_and_has_stable_digest(tmp_path) -> None:
    path = tmp_path / "manifest.json"
    payload = {
        "manifest_version": 1,
        "snapshot_id": "test-snapshot",
        "search": "serious:1",
        "page_size": 100,
        "max_records": 200,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    first = IngestionManifest.from_path(path)
    second = IngestionManifest.from_path(path)

    assert first.digest == second.digest
    assert len(first.digest) == 64


def test_manifest_rejects_unknown_fields(tmp_path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "snapshot_id": "test-snapshot",
                "search": "serious:1",
                "page_size": 100,
                "max_records": 200,
                "unexpected": True,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unknown manifest fields"):
        IngestionManifest.from_path(path)
