import math
from datetime import date

from opensignal.core.models import SignalScore
from opensignal.detection.ror import ContingencyTable
from opensignal.detection.statistics import (
    corrected_cells,
    log_confidence_interval,
    pearson_chi_square,
)


class ProportionalReportingRatio:
    """PRR baseline using transparent Evans-style signal criteria."""

    name = "proportional_reporting_ratio"

    def score(
        self,
        *,
        drug: str,
        event: str,
        analysis_date: date,
        inputs: object,
    ) -> SignalScore:
        if not isinstance(inputs, ContingencyTable):
            raise TypeError("PRR requires a ContingencyTable")

        a, b, c, d = corrected_cells(inputs)
        exposed_rate = a / (a + b)
        comparison_rate = c / (c + d)
        prr = exposed_rate / comparison_rate
        standard_error = math.sqrt(
            (1 / a) - (1 / (a + b)) + (1 / c) - (1 / (c + d))
        )
        lower, upper = log_confidence_interval(prr, standard_error)
        chi_square = pearson_chi_square(inputs)
        criteria = {
            "minimum_case_count": inputs.a >= 3,
            "prr_at_least_two": prr >= 2,
            "chi_square_at_least_four": chi_square >= 4,
        }
        stable = inputs.a >= 5 and lower > 1

        return SignalScore(
            drug=drug,
            event=event,
            analysis_date=analysis_date,
            detector=self.name,
            score=prr,
            lower_bound=lower,
            upper_bound=upper,
            case_count=inputs.a,
            other_events_with_drug=inputs.b,
            target_event_with_other_drugs=inputs.c,
            other_events_with_other_drugs=inputs.d,
            chi_square=chi_square,
            criteria=criteria,
            passes_stability_rule=stable,
            explanation=(
                "Potential reporting signal when there are at least three target "
                "cases, PRR is at least 2, and Pearson chi-square is at least 4. "
                "The conservative stability rule additionally requires five "
                "cases and a lower 95% confidence bound above 1."
            ),
            is_potential_signal=all(criteria.values()),
        )
