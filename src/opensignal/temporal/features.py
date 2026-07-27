from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from opensignal.detection.contingency import (
    ContingencyBuilder,
    DrugEventObservation,
)
from opensignal.detection.prr import ProportionalReportingRatio
from opensignal.detection.ror import ReportingOddsRatio
from opensignal.temporal.models import TemporalFeature


@dataclass(frozen=True)
class TemporalObservation:
    report_id: str
    received_date: date
    drug: str
    event: str
    serious: bool | None


def quarter_key(value: date) -> str:
    return f"{value.year}-Q{((value.month - 1) // 3) + 1}"


def quarter_end(key: str) -> date:
    year = int(key[:4])
    quarter = int(key[-1])
    return date(year, quarter * 3, 31 if quarter in (1, 4) else 30)


def build_temporal_features(
    observations: Iterable[TemporalObservation],
) -> list[TemporalFeature]:
    rows = list(observations)
    candidate_pairs = sorted({(row.drug, row.event) for row in rows})
    by_quarter: dict[str, list[TemporalObservation]] = defaultdict(list)
    for row in rows:
        by_quarter[quarter_key(row.received_date)].append(row)

    previous_counts: dict[tuple[str, str], int] = {}
    features: list[TemporalFeature] = []
    for quarter in sorted(by_quarter):
        quarter_rows = by_quarter[quarter]
        detector_rows = [
            DrugEventObservation(
                report_id=row.report_id,
                received_date=row.received_date,
                drug=row.drug,
                event=row.event,
            )
            for row in quarter_rows
        ]
        builder = ContingencyBuilder(detector_rows)
        report_ids = {row.report_id for row in quarter_rows}
        serious_by_pair: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in quarter_rows:
            if row.serious:
                serious_by_pair[(row.drug, row.event)].add(row.report_id)

        for drug, event in candidate_pairs:
            table = builder.build(drug, event)
            pair = (drug, event)
            previous = previous_counts.get(pair, 0)
            growth = (
                float(table.a - previous) / max(previous, 1)
                if previous or table.a
                else 0.0
            )
            ror = (
                ReportingOddsRatio()
                .score(
                    drug=drug,
                    event=event,
                    analysis_date=builder.analysis_date,
                    inputs=table,
                )
                .score
            )
            prr = (
                ProportionalReportingRatio()
                .score(
                    drug=drug,
                    event=event,
                    analysis_date=builder.analysis_date,
                    inputs=table,
                )
                .score
            )
            features.append(
                TemporalFeature(
                    drug=drug,
                    event=event,
                    quarter=quarter,
                    quarter_end=quarter_end(quarter),
                    report_count=table.a,
                    total_reports=len(report_ids),
                    reporting_share=table.a / len(report_ids),
                    quarter_over_quarter_growth=growth,
                    serious_proportion=(
                        len(serious_by_pair[pair]) / table.a if table.a else 0.0
                    ),
                    ror=ror,
                    prr=prr,
                )
            )
            previous_counts[pair] = table.a
    return features
