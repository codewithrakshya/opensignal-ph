import math

from opensignal.adjusted.statistics import StratumTable, mantel_haenszel_or
from opensignal.detection.ror import ContingencyTable


def test_mantel_haenszel_matches_reference_calculation() -> None:
    strata = [
        StratumTable("younger", ContingencyTable(12, 18, 8, 32)),
        StratumTable("older", ContingencyTable(20, 30, 15, 45)),
    ]
    estimate, lower, upper = mantel_haenszel_or(strata)
    expected = (
        (12 * 32 / 70) + (20 * 45 / 110)
    ) / ((18 * 8 / 70) + (30 * 15 / 110))
    assert math.isclose(estimate, expected)
    assert lower < estimate < upper

