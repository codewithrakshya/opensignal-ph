import json
from datetime import UTC, datetime

from opensignal.adjusted.pipeline import CovariateAdjustedPipeline


def write_adjusted_fixture(data_dir, snapshot_id: str) -> None:
    path = (
        data_dir
        / "curated"
        / "openfda"
        / snapshot_id
        / "drug_event_pairs.jsonl"
    )
    path.parent.mkdir(parents=True)
    rows = []
    report = 0
    for age, sex in (("18-44", "female"), ("45-64", "male"), ("65+", "female")):
        for drug, event, count in (
            ("DRUG A", "EVENT X", 8),
            ("DRUG A", "EVENT Y", 4),
            ("DRUG B", "EVENT X", 3),
            ("DRUG B", "EVENT Y", 10),
        ):
            for _ in range(count):
                report += 1
                rows.append(
                    {
                        "report_id": f"r{report}",
                        "received_date": "2025-01-01",
                        "drug_name": drug,
                        "reaction": event,
                        "patient_age_group": age,
                        "patient_sex": sex,
                    }
                )
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def test_adjusted_pipeline_writes_sensitivity_artifact(tmp_path) -> None:
    write_adjusted_fixture(tmp_path, "adjusted-fixture")
    comparators = tmp_path / "comparators.json"
    comparators.write_text('{"DRUG A": ["DRUG B"]}')
    result = CovariateAdjustedPipeline(
        tmp_path,
        clock=lambda: datetime(2025, 2, 1, tzinfo=UTC),
    ).run("adjusted-fixture", comparator_sets=comparators)
    rows = [
        json.loads(line)
        for line in (tmp_path / result.sensitivity_path).read_text().splitlines()
    ]
    target = next(
        row for row in rows if row["drug"] == "DRUG A" and row["event"] == "EVENT X"
    )
    assert result.results_written == 4
    assert target["crude_ror"] > 1
    assert target["mantel_haenszel"]["estimate"] > 1
    assert target["penalized_logistic"]["estimate"] > 1
    assert target["hierarchical_bayesian"]["lower_bound"] > 1
    assert target["active_comparator"]["estimate"] > 1
    assert len(target["strata"]) == 3
