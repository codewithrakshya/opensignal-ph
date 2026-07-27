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
    explanation: str
    is_potential_signal: bool
