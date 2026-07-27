import hashlib
import json
from datetime import UTC, date, datetime

from opensignal.temporal.pipeline import OpenFDATemporalPipeline


def write_temporal_fixture(data_dir, snapshot_id: str) -> None:
    path = data_dir / "curated" / "openfda" / snapshot_id / "drug_event_pairs.jsonl"
    path.parent.mkdir(parents=True)
    rows = []
    report_number = 0
    for quarter, month in enumerate((1, 4, 7, 10), start=1):
        target_count = 2 if quarter < 4 else 20
        for _ in range(target_count):
            report_number += 1
            rows.append(
                {
                    "report_id": f"target-{report_number}",
                    "received_date": date(2024, month, 10).isoformat(),
                    "drug_name": "DRUG A",
                    "reaction": "EVENT X",
                    "serious": report_number % 2 == 0,
                }
            )
        for index in range(10):
            rows.append(
                {
                    "report_id": f"background-{quarter}-{index}",
                    "received_date": date(2024, month, 12).isoformat(),
                    "drug_name": "DRUG B",
                    "reaction": "EVENT Y",
                    "serious": False,
                }
            )
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_temporal_pipeline_writes_reproducible_artifacts(tmp_path) -> None:
    snapshot_id = "phase4-fixture"
    write_temporal_fixture(tmp_path, snapshot_id)
    pipeline = OpenFDATemporalPipeline(
        tmp_path,
        contamination=0.125,
        minimum_history=3,
        clock=lambda: datetime(2025, 1, 1, tzinfo=UTC),
    )

    first = pipeline.run(snapshot_id)
    first_signals = (tmp_path / first.signals_path).read_bytes()
    first_model_hash = hashlib.sha256(
        (tmp_path / first.model_path).read_bytes()
    ).hexdigest()
    second = pipeline.run(snapshot_id)

    assert first.feature_rows == 8
    assert first.signal_rows == 8
    assert first.anomalies == 1
    assert first.change_points == 1
    assert first_signals == (tmp_path / second.signals_path).read_bytes()
    metadata = json.loads((tmp_path / first.metadata_path).read_text(encoding="utf-8"))
    assert metadata["random_state"] == 42
    assert metadata["model_artifact_sha256"] == first_model_hash
    assert len(metadata["model_input_sha256"]) == 64
