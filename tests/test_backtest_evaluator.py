from datetime import UTC, date, datetime

from opensignal.backtesting.evaluator import evaluate
from opensignal.backtesting.models import ReferenceEntry, ReferenceSet
from opensignal.temporal.models import TemporalFeature


def make_feature(
    quarter: int,
    drug: str,
    event: str,
    count: int,
) -> TemporalFeature:
    return TemporalFeature(
        drug=drug,
        event=event,
        quarter=f"2024-Q{quarter}",
        quarter_end=date(2024, quarter * 3, 31 if quarter in (1, 4) else 30),
        report_count=count,
        total_reports=100,
        reporting_share=count / 100,
        quarter_over_quarter_growth=0,
        serious_proportion=0.5,
        ror=float(count),
        prr=float(count),
    )


def reference_set() -> ReferenceSet:
    return ReferenceSet(
        reference_set_id="synthetic-v1",
        title="Synthetic test reference",
        retrieved_at=datetime(2025, 1, 1, tzinfo=UTC),
        entries=[
            ReferenceEntry(
                reference_id="signal-1",
                signal_quarter="2024-Q3",
                product_text="Drug A",
                risk_text="Event X",
                normalized_drug="DRUG A",
                normalized_event="EVENT X",
                match_method="exact",
                source_url="https://www.fda.gov/example",
            ),
            ReferenceEntry(
                reference_id="unmatched-1",
                signal_quarter="2024-Q3",
                product_text="Product class",
                risk_text="Broad event",
                match_method="unmatched",
                source_url="https://www.fda.gov/example",
            ),
        ],
    )


def feature_table(q4_count: int = 2) -> list[TemporalFeature]:
    rows = []
    for quarter in range(1, 5):
        rows.extend(
            [
                make_feature(
                    quarter,
                    "DRUG A",
                    "EVENT X",
                    30 if quarter == 3 else q4_count if quarter == 4 else 2,
                ),
                make_feature(quarter, "DRUG B", "EVENT Y", 3),
                make_feature(quarter, "DRUG C", "EVENT Z", 1),
            ]
        )
    return rows


def test_walk_forward_metrics_compare_all_detectors() -> None:
    result = evaluate(
        feature_table(),
        reference_set(),
        snapshot_id="snapshot",
        generated_at=datetime(2025, 1, 1, tzinfo=UTC),
        k=1,
        random_state=42,
        minimum_training_rows=6,
    )

    assert {item.detector for item in result.summary.detector_summaries} == {
        "report_count",
        "ror",
        "prr",
        "isolation_forest",
    }
    count_summary = next(
        item
        for item in result.summary.detector_summaries
        if item.detector == "report_count"
    )
    assert count_summary.recall_at_k == 1
    assert count_summary.median_lead_quarters == 0
    assert result.summary.unmatched_references == 1
    assert result.summary.matched_references == 1


def test_future_rows_do_not_change_prior_ml_ranking() -> None:
    first = evaluate(
        feature_table(q4_count=2),
        reference_set(),
        snapshot_id="snapshot",
        generated_at=datetime(2025, 1, 1, tzinfo=UTC),
        k=2,
        random_state=42,
        minimum_training_rows=6,
    )
    second = evaluate(
        feature_table(q4_count=200),
        reference_set(),
        snapshot_id="snapshot",
        generated_at=datetime(2025, 1, 1, tzinfo=UTC),
        k=2,
        random_state=42,
        minimum_training_rows=6,
    )

    def q3_ml(result):
        return [
            (row.drug, row.event, row.rank, row.score)
            for row in result.rankings
            if row.quarter == "2024-Q3" and row.detector == "isolation_forest"
        ]

    assert q3_ml(first) == q3_ml(second)
