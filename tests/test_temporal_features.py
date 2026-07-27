from datetime import date

from opensignal.temporal.features import (
    TemporalObservation,
    build_temporal_features,
    quarter_key,
)


def test_quarter_key() -> None:
    assert quarter_key(date(2025, 1, 1)) == "2025-Q1"
    assert quarter_key(date(2025, 12, 31)) == "2025-Q4"


def test_features_include_zero_count_pair_history() -> None:
    observations = [
        TemporalObservation("r1", date(2024, 1, 2), "A", "X", True),
        TemporalObservation("r2", date(2024, 1, 3), "B", "Y", False),
        TemporalObservation("r3", date(2024, 4, 2), "B", "Y", False),
    ]

    features = build_temporal_features(observations)

    target = [row for row in features if row.drug == "A" and row.event == "X"]
    assert [row.report_count for row in target] == [1, 0]
    assert target[0].serious_proportion == 1
    assert target[1].serious_proportion == 0
    assert target[1].quarter_over_quarter_growth == -1
