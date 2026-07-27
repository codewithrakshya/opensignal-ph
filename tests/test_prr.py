from datetime import date

import pytest

from opensignal.detection import ContingencyTable, ProportionalReportingRatio
from opensignal.detection.statistics import pearson_chi_square


def test_prr_matches_reference_calculation_and_criteria() -> None:
    table = ContingencyTable(a=5, b=1, c=1, d=13)
    result = ProportionalReportingRatio().score(
        drug="DRUG A",
        event="EVENT X",
        analysis_date=date(2025, 1, 31),
        inputs=table,
    )

    expected = (5 / 6) / (1 / 14)
    assert result.score == pytest.approx(expected)
    assert result.chi_square == pytest.approx(pearson_chi_square(table))
    assert result.criteria == {
        "minimum_case_count": True,
        "prr_at_least_two": True,
        "chi_square_at_least_four": True,
    }
    assert result.is_potential_signal is True
    assert result.passes_stability_rule is True


def test_prr_sparse_table_is_finite_and_not_a_signal() -> None:
    result = ProportionalReportingRatio().score(
        drug="DRUG A",
        event="EVENT X",
        analysis_date=date(2025, 1, 31),
        inputs=ContingencyTable(a=1, b=0, c=0, d=10),
    )

    assert result.score > 0
    assert result.is_potential_signal is False
