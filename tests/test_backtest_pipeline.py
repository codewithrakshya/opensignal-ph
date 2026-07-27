import json
from datetime import UTC, datetime

from opensignal.backtesting.pipeline import BacktestPipeline
from opensignal.temporal.pipeline import jsonl_bytes
from tests.test_backtest_evaluator import feature_table


def write_reference(path) -> None:
    path.write_text(
        json.dumps(
            {
                "reference_set_id": "pipeline-reference-v1",
                "title": "Pipeline reference",
                "retrieved_at": "2025-01-01T00:00:00Z",
                "entries": [
                    {
                        "reference_id": "r1",
                        "signal_quarter": "2024-Q3",
                        "product_text": "Drug A",
                        "risk_text": "Event X",
                        "normalized_drug": "DRUG A",
                        "normalized_event": "EVENT X",
                        "match_method": "exact",
                        "source_url": "https://www.fda.gov/example",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_pipeline_writes_reproducible_evaluation_bundle(tmp_path) -> None:
    snapshot_id = "phase5-fixture"
    feature_path = (
        tmp_path / "analytics" / "openfda" / snapshot_id / "temporal" / "features.jsonl"
    )
    feature_path.parent.mkdir(parents=True)
    feature_path.write_bytes(jsonl_bytes(feature_table()))
    reference_path = tmp_path / "reference.json"
    write_reference(reference_path)
    pipeline = BacktestPipeline(
        tmp_path,
        k=1,
        minimum_training_rows=6,
        clock=lambda: datetime(2025, 1, 1, tzinfo=UTC),
    )

    first = pipeline.run(snapshot_id, reference_path)
    first_summary = (tmp_path / first.summary_path).read_bytes()
    second = pipeline.run(snapshot_id, reference_path)

    assert first.ranking_rows > 0
    assert first.metric_rows == 16
    assert first_summary == (tmp_path / second.summary_path).read_bytes()
    metadata = json.loads((tmp_path / first.metadata_path).read_text(encoding="utf-8"))
    assert len(metadata["feature_input_sha256"]) == 64
    assert len(metadata["reference_input_sha256"]) == 64
