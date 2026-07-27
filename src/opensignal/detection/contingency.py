from dataclasses import dataclass
from datetime import date

from opensignal.detection.ror import ContingencyTable


@dataclass(frozen=True)
class DrugEventObservation:
    report_id: str
    received_date: date
    drug: str
    event: str


class ContingencyBuilder:
    """Build report-level two-by-two tables from curated drug-event rows."""

    def __init__(self, observations: list[DrugEventObservation]) -> None:
        if not observations:
            raise ValueError("At least one curated observation is required")
        self.observations = observations
        self.all_reports = {item.report_id for item in observations}
        self.analysis_date = max(item.received_date for item in observations)
        self.drug_reports: dict[str, set[str]] = {}
        self.event_reports: dict[str, set[str]] = {}
        self.observed_pairs: set[tuple[str, str]] = set()
        for item in observations:
            self.drug_reports.setdefault(item.drug, set()).add(item.report_id)
            self.event_reports.setdefault(item.event, set()).add(item.report_id)
            self.observed_pairs.add((item.drug, item.event))

    def build(self, drug: str, event: str) -> ContingencyTable:
        drug_reports = self.drug_reports.get(drug, set())
        event_reports = self.event_reports.get(event, set())
        both = drug_reports & event_reports
        return ContingencyTable(
            a=len(both),
            b=len(drug_reports - event_reports),
            c=len(event_reports - drug_reports),
            d=len(self.all_reports - (drug_reports | event_reports)),
        )

    def candidate_pairs(self) -> list[tuple[str, str]]:
        return sorted(self.observed_pairs)
