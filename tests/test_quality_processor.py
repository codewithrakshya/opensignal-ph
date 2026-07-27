import json
from datetime import UTC, datetime
from pathlib import Path

from opensignal.ingestion.storage import RawSnapshotStore
from opensignal.quality.processor import OpenFDAQualityProcessor


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def test_processor_validates_deduplicates_normalizes_and_reports(tmp_path) -> None:
    snapshot_id = "quality-fixture"
    fixture = Path(__file__).parent / "fixtures" / "openfda" / "quality_records.json"
    records = json.loads(fixture.read_text(encoding="utf-8"))
    store = RawSnapshotStore(tmp_path, snapshot_id, source="openfda")
    store.write_page(
        0,
        {
            "retrieval": {"retrieved_at": "2025-01-01T00:00:00+00:00"},
            "response": {"results": records},
        },
    )

    def clock() -> datetime:
        return datetime(2025, 1, 1, tzinfo=UTC)

    result = OpenFDAQualityProcessor(tmp_path, clock=clock).process(snapshot_id)

    assert result.accepted_reports == 2
    assert result.rejected_records == 2
    assert result.curated_rows == 3

    curated_path = (
        tmp_path
        / "curated"
        / "openfda"
        / snapshot_id
        / "drug_event_pairs.jsonl"
    )
    curated = read_jsonl(curated_path)
    assert {(row["drug_name"], row["reaction"]) for row in curated} == {
        ("ASPIRIN", "HEADACHE"),
        ("ASPIRIN", "NAUSEA"),
        ("DRUG X", "RASH"),
    }
    aspirin = next(row for row in curated if row["drug_name"] == "ASPIRIN")
    assert aspirin["report_version"] == 2
    assert aspirin["drug_role"] == "primary_suspect"
    assert aspirin["drug_name_source"] == "openfda_generic_name"

    rejected_path = (
        tmp_path / "validated" / "openfda" / snapshot_id / "rejected.jsonl"
    )
    rejected = read_jsonl(rejected_path)
    assert {row["report_id"] for row in rejected} == {"300", "400"}
    assert all(row["raw_sha256"] for row in rejected)

    report_path = tmp_path / result.quality_report_path
    report = json.loads(report_path.read_text(encoding="utf-8"))
    metrics = report["metrics"]
    assert metrics["input_records"] == 6
    assert metrics["schema_valid_records"] == 5
    assert metrics["required_field_completeness"]["patient"] == 0.8333
    assert metrics["followup_records_removed"] == 1
    assert metrics["exact_duplicates_removed"] == 1
    assert metrics["accepted_reports"] == 2
    assert metrics["drug_name_fallbacks"] == 1
    assert report["checks"][1]["status"] == "warn"
    assert report["checks"][2]["name"] == "required_field_completeness"


def test_raw_snapshot_storage_is_source_neutral(tmp_path) -> None:
    store = RawSnapshotStore(
        tmp_path,
        "example-snapshot",
        source="cdc-example",
    )
    page = store.write_page(
        0,
        {
            "retrieval": {},
            "response": {"results": [{"value": 1}]},
        },
    )

    assert page.path.startswith("raw/cdc-example/example-snapshot/")
    assert store.verify_page(page)
