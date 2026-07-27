from fastapi.testclient import TestClient

from opensignal.api.main import app
from opensignal.backtesting.pipeline import BacktestPipeline
from opensignal.core.config import get_settings
from opensignal.temporal.pipeline import jsonl_bytes
from tests.test_backtest_evaluator import feature_table
from tests.test_backtest_pipeline import write_reference


def test_backtest_api_returns_saved_summary(tmp_path) -> None:
    snapshot_id = "backtest-api-fixture"
    feature_path = (
        tmp_path / "analytics" / "openfda" / snapshot_id / "temporal" / "features.jsonl"
    )
    feature_path.parent.mkdir(parents=True)
    feature_path.write_bytes(jsonl_bytes(feature_table()))
    reference_path = tmp_path / "reference.json"
    write_reference(reference_path)
    BacktestPipeline(tmp_path, k=1, minimum_training_rows=6).run(
        snapshot_id, reference_path
    )
    get_settings().data_dir = tmp_path

    response = TestClient(app).get(
        f"/backtests/openfda/{snapshot_id}/pipeline-reference-v1"
    )

    assert response.status_code == 200
    assert response.json()["reference_set_id"] == "pipeline-reference-v1"
    assert len(response.json()["detector_summaries"]) == 4
