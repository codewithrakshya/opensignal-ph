import math
from dataclasses import dataclass

from opensignal.detection.prr import ProportionalReportingRatio
from opensignal.detection.ror import ContingencyTable, ReportingOddsRatio


@dataclass(frozen=True)
class StratumTable:
    name: str
    table: ContingencyTable


def mantel_haenszel_or(
    strata: list[StratumTable],
) -> tuple[float, float, float]:
    """Return MH odds ratio and Robins-Breslow-Greenland confidence limits."""
    corrected: list[tuple[float, float, float, float, float]] = []
    for item in strata:
        values = item.table.a, item.table.b, item.table.c, item.table.d
        correction = 0.5 if 0 in values else 0.0
        a, b, c, d = (float(value) + correction for value in values)
        corrected.append((a, b, c, d, a + b + c + d))
    r_value = sum(a * d / n for a, _, _, d, n in corrected)
    s_value = sum(b * c / n for _, b, c, _, n in corrected)
    if r_value <= 0 or s_value <= 0:
        return 1.0, 0.0, math.inf
    estimate = r_value / s_value
    first = sum(
        (a + d) * a * d / (n * n) for a, _, _, d, n in corrected
    ) / (2 * r_value * r_value)
    middle = sum(
        ((a + d) * b * c + (b + c) * a * d) / (n * n)
        for a, b, c, d, n in corrected
    ) / (2 * r_value * s_value)
    last = sum(
        (b + c) * b * c / (n * n) for _, b, c, _, n in corrected
    ) / (2 * s_value * s_value)
    standard_error = math.sqrt(max(first + middle + last, 0.0))
    return (
        estimate,
        math.exp(math.log(estimate) - 1.96 * standard_error),
        math.exp(math.log(estimate) + 1.96 * standard_error),
    )


def stratum_estimates(
    strata: list[StratumTable],
) -> list[tuple[StratumTable, float, float, float, float]]:
    ror = ReportingOddsRatio()
    prr = ProportionalReportingRatio()
    output = []
    for item in strata:
        ror_score = ror.score(
            drug="TARGET",
            event="TARGET",
            analysis_date=__import__("datetime").date.today(),
            inputs=item.table,
        )
        prr_score = prr.score(
            drug="TARGET",
            event="TARGET",
            analysis_date=__import__("datetime").date.today(),
            inputs=item.table,
        )
        output.append(
            (
                item,
                ror_score.score,
                ror_score.lower_bound or 0.0,
                ror_score.upper_bound or math.inf,
                prr_score.score,
            )
        )
    return output


def heterogeneity(
    estimates: list[tuple[StratumTable, float, float, float, float]],
) -> tuple[float, int, float | None]:
    usable = [item for item in estimates if item[1] > 0 and item[2] > 0]
    if len(usable) < 2:
        return 0.0, 0, None
    weighted: list[tuple[float, float]] = []
    for _, estimate, lower, upper, _ in usable:
        standard_error = (math.log(upper) - math.log(lower)) / (2 * 1.96)
        if standard_error > 0:
            weighted.append((math.log(estimate), 1 / (standard_error**2)))
    if len(weighted) < 2:
        return 0.0, 0, None
    mean = sum(value * weight for value, weight in weighted) / sum(
        weight for _, weight in weighted
    )
    q_value = sum(
        weight * ((value - mean) ** 2) for value, weight in weighted
    )
    degrees = len(weighted) - 1
    # Wilson-Hilferty approximation to the upper chi-square tail.
    z_value = (
        (q_value / degrees) ** (1 / 3) - (1 - 2 / (9 * degrees))
    ) / math.sqrt(2 / (9 * degrees))
    p_value = 0.5 * math.erfc(z_value / math.sqrt(2))
    return q_value, degrees, min(max(p_value, 0.0), 1.0)

