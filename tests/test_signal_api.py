from fastapi.testclient import TestClient

from opensignal.api.main import app
from opensignal.core.config import get_settings
from opensignal.detection.pipeline import OpenFDAScoringPipeline
from tests.test_scoring_pipeline import write_curated_fixture


def test_signal_api_filters_versioned_artifact(tmp_path) -> None:
    snapshot_id = "api-signal-fixture"
    write_curated_fixture(tmp_path, snapshot_id)
    OpenFDAScoringPipeline(tmp_path).run(snapshot_id)
    get_settings().data_dir = tmp_path

    response = TestClient(app).get(
        f"/signals/openfda/{snapshot_id}",
        params={
            "detector": "proportional_reporting_ratio",
            "drug": "drug a",
            "event": "event x",
            "potential_only": "true",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["case_count"] == 5
    assert payload[0]["criteria"]["prr_at_least_two"] is True


def test_signal_api_rejects_unsafe_snapshot_id() -> None:
    response = TestClient(app).get("/signals/openfda/not.safe")

    assert response.status_code == 400
