from datetime import date

from opensignal.temporal.detector import (
    fit_temporal_detector,
    robust_change_scores,
)
from opensignal.temporal.models import TemporalFeature


def feature(quarter: int, count: int) -> TemporalFeature:
    return TemporalFeature(
        drug="DRUG A",
        event="EVENT X",
        quarter=f"2024-Q{quarter}",
        quarter_end=date(2024, quarter * 3, 31 if quarter in (1, 4) else 30),
        report_count=count,
        total_reports=max(count, 10),
        reporting_share=count / max(count, 10),
        quarter_over_quarter_growth=0,
        serious_proportion=0.5,
        ror=1,
        prr=1,
    )


def test_change_point_uses_only_prior_history() -> None:
    rows = [feature(index, count) for index, count in enumerate([2, 2, 2, 20], 1)]

    scores = robust_change_scores(rows, minimum_history=3)

    assert scores[("DRUG A", "EVENT X", "2024-Q3")][0] == 0
    assert scores[("DRUG A", "EVENT X", "2024-Q4")][1] is True
    assert scores[("DRUG A", "EVENT X", "2024-Q4")][2] == 3


def test_isolation_forest_is_reproducible() -> None:
    rows = [feature(index, count) for index, count in enumerate([1, 2, 2, 30], 1)]

    _, first = fit_temporal_detector(
        rows, contamination=0.25, random_state=42, minimum_history=3
    )
    _, second = fit_temporal_detector(
        rows, contamination=0.25, random_state=42, minimum_history=3
    )

    assert [row.anomaly_score for row in first] == [row.anomaly_score for row in second]
    assert sum(row.is_anomaly for row in first) == 1
    assert list(first[-1].feature_contributions)[:2] == [
        "report_count",
        "reporting_share",
    ]
