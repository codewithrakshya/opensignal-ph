import math
from dataclasses import dataclass
from datetime import date

from opensignal.core.models import SignalScore


@dataclass(frozen=True)
class ContingencyTable:
    """Two-by-two table used for disproportionality analysis.

    a: target drug with target event
    b: target drug with other events
    c: other drugs with target event
    d: other drugs with other events
    """

    a: int
    b: int
    c: int
    d: int

    def __post_init__(self) -> None:
        if min(self.a, self.b, self.c, self.d) < 0:
            raise ValueError("Contingency-table counts cannot be negative")


class ReportingOddsRatio:
    """Interpretable disproportionality baseline with a 95% confidence interval."""

    name = "reporting_odds_ratio"

    def score(
        self,
        *,
        drug: str,
        event: str,
        analysis_date: date,
        inputs: object,
    ) -> SignalScore:
        if not isinstance(inputs, ContingencyTable):
            raise TypeError("ROR requires a ContingencyTable")

        # Haldane-Anscombe correction keeps sparse tables finite.
        a, b, c, d = (value + 0.5 for value in (inputs.a, inputs.b, inputs.c, inputs.d))
        ror = (a * d) / (b * c)
        standard_error = math.sqrt((1 / a) + (1 / b) + (1 / c) + (1 / d))
        lower = math.exp(math.log(ror) - 1.96 * standard_error)
        upper = math.exp(math.log(ror) + 1.96 * standard_error)
        is_signal = inputs.a >= 3 and lower > 1

        return SignalScore(
            drug=drug,
            event=event,
            analysis_date=analysis_date,
            detector=self.name,
            score=ror,
            lower_bound=lower,
            upper_bound=upper,
            case_count=inputs.a,
            explanation=(
                "Potential reporting signal when there are at least three target "
                "cases and the lower 95% confidence bound exceeds 1."
            ),
            is_potential_signal=is_signal,
        )
