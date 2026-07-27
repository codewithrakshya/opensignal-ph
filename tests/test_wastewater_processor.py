import json
from datetime import UTC, datetime
from pathlib import Path

from opensignal.ingestion.storage import RawSnapshotStore
from opensignal.quality.wastewater import CDCWastewaterQualityProcessor


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def test_wastewater_processor_validates_deduplicates_and_reports(tmp_path) -> None:
    snapshot_id = "cdc-quality-fixture"
    fixture = Path(__file__).parent / "fixtures" / "socrata" / "wastewater_records.json"
    records = json.loads(fixture.read_text(encoding="utf-8"))
    store = RawSnapshotStore(
        tmp_path,
        snapshot_id,
        source="cdc-wastewater",
    )
    store.write_page(
        0,
        {
            "retrieval": {},
            "response": {"results": records},
        },
    )

    def clock() -> datetime:
        return datetime(2026, 1, 20, tzinfo=UTC)

    result = CDCWastewaterQualityProcessor(tmp_path, clock=clock).process(
        snapshot_id
    )

    assert result.accepted_reports == 2
    assert result.rejected_records == 2
    assert result.curated_rows == 2

    curated_path = (
        tmp_path
        / "curated"
        / "cdc-wastewater"
        / snapshot_id
        / "observations.jsonl"
    )
    curated = read_jsonl(curated_path)
    assert {row["record_id"] for row in curated} == {"a", "b"}
    latest = next(row for row in curated if row["record_id"] == "a")
    assert latest["concentration"] == 12.5
    assert latest["state_territory"] == "CA"
    assert latest["pathogen"] == "SARS-COV-2"

    report = json.loads(
        (tmp_path / result.quality_report_path).read_text(encoding="utf-8")
    )
    metrics = report["metrics"]
    assert metrics["input_records"] == 6
    assert metrics["schema_valid_records"] == 4
    assert metrics["superseded_records_removed"] == 1
    assert metrics["exact_duplicates_removed"] == 1
    assert metrics["missing_concentration_records"] == 1
    assert report["source"] == "cdc-wastewater"
    assert "should not be compared directly" in report["interpretation_notes"][0]
