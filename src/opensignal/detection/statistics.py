import math

from opensignal.detection.ror import ContingencyTable


def pearson_chi_square(table: ContingencyTable) -> float:
    """Return the uncorrected Pearson chi-square for a two-by-two table."""
    a, b, c, d = table.a, table.b, table.c, table.d
    total = a + b + c + d
    denominator = (a + b) * (c + d) * (a + c) * (b + d)
    if total == 0 or denominator == 0:
        return 0
    numerator = total * ((a * d - b * c) ** 2)
    return numerator / denominator


def corrected_cells(table: ContingencyTable) -> tuple[float, float, float, float]:
    """Apply the Haldane-Anscombe correction to keep sparse estimates finite."""
    correction = 0.5 if 0 in (table.a, table.b, table.c, table.d) else 0
    a, b, c, d = (
        float(value + correction)
        for value in (table.a, table.b, table.c, table.d)
    )
    return a, b, c, d


def log_confidence_interval(
    estimate: float,
    standard_error: float,
) -> tuple[float, float]:
    return (
        math.exp(math.log(estimate) - 1.96 * standard_error),
        math.exp(math.log(estimate) + 1.96 * standard_error),
    )
