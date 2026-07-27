import json

import pytest

from opensignal.ingestion.socrata_manifest import SocrataManifest


def test_socrata_manifest_loads_and_has_stable_digest(tmp_path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "source": "cdc-wastewater",
                "snapshot_id": "cdc-test-snapshot",
                "domain": "data.cdc.gov",
                "dataset_id": "j9g8-acpt",
                "page_size": 100,
                "max_records": 200,
            }
        ),
        encoding="utf-8",
    )

    manifest = SocrataManifest.from_path(path)

    assert manifest.source == "cdc-wastewater"
    assert len(manifest.digest) == 64
    assert manifest.order == ":id"


def test_socrata_manifest_rejects_invalid_dataset_id() -> None:
    with pytest.raises(ValueError, match="xxxx-xxxx"):
        SocrataManifest(
            1,
            "cdc-wastewater",
            "cdc-test-snapshot",
            "data.cdc.gov",
            "invalid",
            100,
            200,
        )
