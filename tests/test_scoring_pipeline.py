import json
from datetime import UTC, date, datetime, timedelta

from opensignal.detection.pipeline import OpenFDAScoringPipeline


def write_curated_fixture(data_dir, snapshot_id: str) -> None:
    path = (
        data_dir
        / "curated"
        / "openfda"
        / snapshot_id
        / "drug_event_pairs.jsonl"
    )
    path.parent.mkdir(parents=True)
    pairs = (
        [("DRUG A", "EVENT X")] * 5
        + [("DRUG A", "EVENT Y")]
        + [("DRUG B", "EVENT X")]
        + [("DRUG B", "EVENT Y")] * 13
    )
    start = date(2025, 1, 1)
    rows = [
        {
            "report_id": f"r{index:02d}",
            "received_date": (start + timedelta(days=index)).isoformat(),
            "drug_name": drug,
            "reaction": event,
        }
        for index, (drug, event) in enumerate(pairs, start=1)
    ]
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_pipeline_writes_versioned_scores_and_metadata(tmp_path) -> None:
    snapshot_id = "phase3-fixture"
    write_curated_fixture(tmp_path, snapshot_id)

    def clock() -> datetime:
        return datetime(2025, 2, 1, tzinfo=UTC)

    result = OpenFDAScoringPipeline(tmp_path, clock=clock).run(snapshot_id)

    assert result.scores_written == 8
    assert result.potential_signals >= 2
    assert result.stable_signals >= 2

    scores = [
        json.loads(line)
        for line in (tmp_path / result.signals_path)
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    target = [
        score
        for score in scores
        if score["drug"] == "DRUG A" and score["event"] == "EVENT X"
    ]
    assert {score["detector"] for score in target} == {
        "reporting_odds_ratio",
        "proportional_reporting_ratio",
    }
    assert all(score["case_count"] == 5 for score in target)
    assert all(score["other_events_with_drug"] == 1 for score in target)
    assert all(score["target_event_with_other_drugs"] == 1 for score in target)
    assert all(score["other_events_with_other_drugs"] == 13 for score in target)

    metadata = json.loads(
        (tmp_path / result.metadata_path).read_text(encoding="utf-8")
    )
    assert metadata["unique_reports"] == 20
    assert metadata["candidate_pairs"] == 4
    assert len(metadata["curated_input_sha256"]) == 64
