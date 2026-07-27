from datetime import date

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str


class SignalScore(BaseModel):
    """Detector output shared by statistical and ML methods."""

    drug: str
    event: str
    analysis_date: date
    detector: str
    score: float
    lower_bound: float | None = None
    upper_bound: float | None = None
    case_count: int = Field(ge=0)
    other_events_with_drug: int = Field(default=0, ge=0)
    target_event_with_other_drugs: int = Field(default=0, ge=0)
    other_events_with_other_drugs: int = Field(default=0, ge=0)
    chi_square: float | None = None
    criteria: dict[str, bool] = Field(default_factory=dict)
    passes_stability_rule: bool = False
    explanation: str
    is_potential_signal: bool
