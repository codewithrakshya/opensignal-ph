from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

MatchMethod = Literal["exact", "manual", "unmatched"]


class ReferenceEntry(BaseModel):
    reference_id: str
    signal_quarter: str = Field(pattern=r"^\d{4}-Q[1-4]$")
    product_text: str
    risk_text: str
    normalized_drug: str | None = None
    normalized_event: str | None = None
    match_method: MatchMethod
    match_notes: str | None = None
    source_url: str

    @model_validator(mode="after")
    def validate_match(self) -> "ReferenceEntry":
        has_pair = (
            self.normalized_drug is not None and self.normalized_event is not None
        )
        if self.match_method == "unmatched" and has_pair:
            raise ValueError("Unmatched references cannot contain a normalized pair")
        if self.match_method != "unmatched" and not has_pair:
            raise ValueError("Matched references require both normalized fields")
        return self


class ReferenceSet(BaseModel):
    schema_version: int = 1
    reference_set_id: str
    title: str
    publisher: str = "U.S. Food and Drug Administration"
    retrieved_at: datetime
    entries: list[ReferenceEntry]


class RankingRow(BaseModel):
    quarter: str
    detector: str
    rank: int = Field(ge=1)
    drug: str
    event: str
    score: float
    is_reference_signal: bool
    matched_reference_ids: list[str]


class QuarterMetric(BaseModel):
    quarter: str
    detector: str
    available: bool
    k: int = Field(ge=1)
    eligible_references: int = Field(ge=0)
    hits: int = Field(ge=0)
    alerts: int = Field(ge=0)
    recall_at_k: float | None
    precision_at_k: float | None


class DetectorSummary(BaseModel):
    detector: str
    evaluated_quarters: int = Field(ge=0)
    eligible_references: int = Field(ge=0)
    hits: int = Field(ge=0)
    recall_at_k: float | None
    precision_at_k: float | None
    median_lead_quarters: float | None
    detected_with_lead_time: int = Field(ge=0)
    alert_burden: int = Field(ge=0)


class BacktestSummary(BaseModel):
    artifact_version: int = 1
    source: str = "openfda"
    snapshot_id: str
    reference_set_id: str
    generated_at: datetime
    k: int
    minimum_training_rows: int
    total_references: int
    matched_references: int
    unmatched_references: int
    out_of_window_references: int
    match_method_counts: dict[str, int]
    detector_summaries: list[DetectorSummary]
    interpretation: str


class BacktestMetadata(BaseModel):
    artifact_version: int = 1
    snapshot_id: str
    reference_set_id: str
    feature_input_path: str
    feature_input_sha256: str
    reference_input_path: str
    reference_input_sha256: str
    evaluation_version: str = "phase5-walk-forward-v1"
    detectors: list[str]
    k: int
    random_state: int
    minimum_training_rows: int
