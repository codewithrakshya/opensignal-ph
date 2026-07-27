from datetime import datetime

from pydantic import BaseModel, Field


class StratumEstimate(BaseModel):
    stratum: str
    reports: int = Field(ge=0)
    cases: int = Field(ge=0)
    ror: float
    prr: float
    lower_bound: float
    upper_bound: float


class AdjustedEstimate(BaseModel):
    method: str
    estimate: float
    lower_bound: float | None = None
    upper_bound: float | None = None
    covariates: list[str]
    reports_used: int
    reports_excluded_missing: int
    interpretation: str


class SensitivityResult(BaseModel):
    artifact_version: int = 1
    source: str = "openfda"
    snapshot_id: str
    drug: str
    event: str
    generated_at: datetime
    crude_ror: float
    crude_lower: float
    crude_upper: float
    mantel_haenszel: AdjustedEstimate
    penalized_logistic: AdjustedEstimate
    hierarchical_bayesian: AdjustedEstimate
    active_comparator: AdjustedEstimate | None = None
    strata: list[StratumEstimate]
    heterogeneity_q: float
    heterogeneity_df: int
    heterogeneity_p_approx: float | None
    caveat: str = (
        "These are adjusted reporting associations from spontaneous reports. "
        "They do not estimate incidence, relative risk, or causality."
    )


class AdjustedRunMetadata(BaseModel):
    artifact_version: int = 1
    source: str = "openfda"
    snapshot_id: str
    generated_at: datetime
    curated_input_sha256: str
    criteria_version: str = "phase9-adjusted-v1"
    covariates: list[str] = ["patient_age_group", "patient_sex", "calendar_year"]
    results_written: int
