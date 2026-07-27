from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class EvidenceDocument(BaseModel):
    document_id: str
    title: str
    publisher: str
    url: HttpUrl
    published_date: date | None = None
    content: str


class RetrievedEvidence(BaseModel):
    document_id: str
    title: str
    publisher: str
    url: HttpUrl
    published_date: date | None = None
    excerpt: str
    relevance_score: float = Field(ge=0, le=1)


class DraftClaim(BaseModel):
    text: str
    citation_ids: list[str] = Field(min_length=1)


class DraftBrief(BaseModel):
    status: Literal["generated", "abstained"]
    headline: str
    claims: list[DraftClaim] = Field(default_factory=list)
    uncertainty: str
    recommended_review_steps: list[str] = Field(default_factory=list)
    abstention_reason: str | None = None


class EvidenceCitation(BaseModel):
    citation_id: str
    document_id: str
    title: str
    publisher: str
    url: HttpUrl
    excerpt: str


class EvidenceBrief(BaseModel):
    artifact_version: int = 1
    source: str
    snapshot_id: str
    drug: str
    event: str
    generated_at: datetime
    status: Literal["generated", "abstained"]
    headline: str
    claims: list[DraftClaim] = Field(default_factory=list)
    uncertainty: str
    recommended_review_steps: list[str] = Field(default_factory=list)
    abstention_reason: str | None = None
    citations: list[EvidenceCitation] = Field(default_factory=list)
    provider: str
    model: str
    prompt_version: str = "phase7-v1"
    signal_artifact_sha256: str
    evidence_set_sha256: str

