from fastapi.testclient import TestClient

from opensignal.adjusted.pipeline import CovariateAdjustedPipeline
from opensignal.api.main import app
from opensignal.core.config import get_settings
from opensignal.detection.pipeline import OpenFDAScoringPipeline
from tests.test_adjusted_pipeline import write_adjusted_fixture


def test_adjusted_api_filters_saved_artifact(tmp_path) -> None:
    snapshot = "adjusted-api"
    write_adjusted_fixture(tmp_path, snapshot)
    OpenFDAScoringPipeline(tmp_path).run(snapshot)
    CovariateAdjustedPipeline(tmp_path).run(snapshot)
    get_settings().data_dir = tmp_path

    response = TestClient(app).get(
        f"/adjusted/openfda/{snapshot}",
        params={"drug": "drug a", "event": "event x"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["mantel_haenszel"]["estimate"] > 1
