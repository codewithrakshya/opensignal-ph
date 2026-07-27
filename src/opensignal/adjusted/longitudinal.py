from datetime import date
from typing import Protocol

from pydantic import BaseModel, Field, model_validator


class LongitudinalCohortRecord(BaseModel):
    """Minimum claims/EHR contract for a future active-comparator analysis."""

    person_id: str
    cohort: str
    exposure_start: date
    observation_start: date
    observation_end: date
    outcome_date: date | None = None
    age: int = Field(ge=0, le=130)
    sex: str
    baseline_covariates: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_timeline(self) -> "LongitudinalCohortRecord":
        if not self.observation_start <= self.exposure_start <= self.observation_end:
            raise ValueError("exposure must fall within the observation window")
        if self.outcome_date and not (
            self.exposure_start <= self.outcome_date <= self.observation_end
        ):
            raise ValueError("outcome must occur after exposure and during follow-up")
        return self


class LongitudinalEstimate(BaseModel):
    method: str
    effect_measure: str
    estimate: float
    lower_bound: float
    upper_bound: float
    exposed_people: int
    comparator_people: int
    diagnostics: dict[str, float]
    caveat: str


class LongitudinalValidator(Protocol):
    """Adapter boundary for governed claims/EHR causal follow-up."""

    name: str

    def estimate(
        self,
        records: list[LongitudinalCohortRecord],
    ) -> LongitudinalEstimate: ...


def validate_cohort_contract(records: list[LongitudinalCohortRecord]) -> None:
    if not records:
        raise ValueError("Longitudinal validation requires cohort records")
    people = [record.person_id for record in records]
    if len(people) != len(set(people)):
        raise ValueError("Each person must appear once in the new-user cohort")
    cohorts = {record.cohort for record in records}
    if len(cohorts) != 2:
        raise ValueError("An active-comparator design requires exactly two cohorts")
    for record in records:
        if (record.exposure_start - record.observation_start).days < 180:
            raise ValueError("At least 180 days of baseline observation is required")

