from datetime import date, datetime

from pydantic import BaseModel, Field


class TemporalFeature(BaseModel):
    drug: str
    event: str
    quarter: str
    quarter_end: date
    report_count: int = Field(ge=0)
    total_reports: int = Field(ge=0)
    reporting_share: float = Field(ge=0)
    quarter_over_quarter_growth: float
    serious_proportion: float = Field(ge=0, le=1)
    ror: float = Field(ge=0)
    prr: float = Field(ge=0)


class TemporalSignal(BaseModel):
    drug: str
    event: str
    quarter: str
    quarter_end: date
    detector: str
    anomaly_score: float
    is_anomaly: bool
    change_score: float
    is_change_point: bool
    baseline_quarters: int = Field(ge=0)
    feature_contributions: dict[str, float]
    explanation: str


class TemporalRunMetadata(BaseModel):
    artifact_version: int = 1
    source: str = "openfda"
    snapshot_id: str
    generated_at: datetime
    curated_input_path: str
    curated_input_sha256: str
    feature_schema_version: str = "phase4-features-v1"
    detector_version: str = "phase4-isolation-forest-v1"
    random_state: int
    contamination: float
    minimum_history_quarters: int
    feature_names: list[str]
    feature_rows: int
    signal_rows: int
    model_input_sha256: str
    model_artifact_path: str
    model_artifact_sha256: str
