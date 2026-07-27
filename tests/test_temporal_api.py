from fastapi.testclient import TestClient

from opensignal.api.main import app
from opensignal.core.config import get_settings
from opensignal.temporal.pipeline import OpenFDATemporalPipeline
from tests.test_temporal_pipeline import write_temporal_fixture


def test_temporal_api_filters_anomalies(tmp_path) -> None:
    snapshot_id = "temporal-api-fixture"
    write_temporal_fixture(tmp_path, snapshot_id)
    OpenFDATemporalPipeline(tmp_path, contamination=0.125, minimum_history=3).run(
        snapshot_id
    )
    get_settings().data_dir = tmp_path

    response = TestClient(app).get(
        f"/temporal-signals/openfda/{snapshot_id}",
        params={"anomalies_only": "true"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["detector"] == "isolation_forest"
    assert payload[0]["feature_contributions"]
