from datetime import date

import pytest

from opensignal.detection import ContingencyTable, ReportingOddsRatio


def test_ror_matches_reference_calculation() -> None:
    result = ReportingOddsRatio().score(
        drug="example-drug",
        event="example-event",
        analysis_date=date(2024, 12, 31),
        inputs=ContingencyTable(a=10, b=90, c=20, d=880),
    )

    expected = (10 * 880) / (90 * 20)
    assert result.score == pytest.approx(expected)
    assert result.case_count == 10
    assert result.is_potential_signal is True


def test_ror_rejects_negative_counts() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        ContingencyTable(a=-1, b=2, c=3, d=4)


def test_sparse_table_is_finite() -> None:
    result = ReportingOddsRatio().score(
        drug="example-drug",
        event="rare-event",
        analysis_date=date(2024, 12, 31),
        inputs=ContingencyTable(a=0, b=10, c=2, d=100),
    )

    assert result.score > 0
    assert result.is_potential_signal is False
