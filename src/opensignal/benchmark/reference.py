import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

ReviewStatus = Literal["seeded_unverified", "independently_reviewed", "rejected"]
MatchMethod = Literal["exact", "manual", "unmatched"]


def quarter_index(value: str) -> int:
    year, quarter = value.split("-Q")
    return int(year) * 4 + int(quarter)


class BenchmarkReferenceEntry(BaseModel):
    reference_id: str
    publication_quarter: str = Field(pattern=r"^\d{4}-Q[1-4]$")
    source_url: HttpUrl
    source_product_text: str
    source_event_text: str
    normalized_drugs: list[str] = Field(default_factory=list)
    normalized_events: list[str] = Field(default_factory=list)
    match_method: MatchMethod = "unmatched"
    review_status: ReviewStatus = "seeded_unverified"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_review(self) -> "BenchmarkReferenceEntry":
        has_mapping = bool(self.normalized_drugs and self.normalized_events)
        if self.match_method == "unmatched" and has_mapping:
            raise ValueError("Unmatched reference cannot contain normalized mappings")
        if self.match_method != "unmatched" and not has_mapping:
            raise ValueError("Matched reference requires drug and event mappings")
        if self.review_status == "independently_reviewed":
            if not self.reviewed_by or not self.reviewed_at:
                raise ValueError("Independent review requires reviewer and timestamp")
            if not has_mapping:
                raise ValueError("Reviewed reference must have normalized mappings")
        return self

    def eligibility(self, analysis_quarter: str) -> tuple[bool, str]:
        if self.review_status != "independently_reviewed":
            return False, "not_independently_reviewed"
        if self.match_method == "unmatched":
            return False, "unmatched_terminology"
        if quarter_index(self.publication_quarter) > quarter_index(analysis_quarter):
            return False, "not_yet_published"
        return True, "eligible"


class BenchmarkReferenceSet(BaseModel):
    schema_version: int = 1
    reference_set_id: str
    title: str
    publisher: str = "U.S. Food and Drug Administration"
    source_index: HttpUrl
    retrieved_at: datetime
    entries: list[BenchmarkReferenceEntry]

    @model_validator(mode="after")
    def unique_ids(self) -> "BenchmarkReferenceSet":
        ids = [entry.reference_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("Benchmark reference set contains duplicate IDs")
        return self

    @classmethod
    def from_path(cls, path: Path) -> "BenchmarkReferenceSet":
        if not path.exists():
            raise FileNotFoundError(f"Benchmark reference set not found: {path}")
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def validation_summary(self, analysis_quarter: str) -> dict[str, object]:
        reasons = Counter(
            entry.eligibility(analysis_quarter)[1] for entry in self.entries
        )
        return {
            "reference_set_id": self.reference_set_id,
            "analysis_quarter": analysis_quarter,
            "total_entries": len(self.entries),
            "eligible_entries": reasons["eligible"],
            "exclusion_counts": {
                reason: count
                for reason, count in sorted(reasons.items())
                if reason != "eligible"
            },
        }

    def write_validation_summary(
        self, analysis_quarter: str, output_path: Path
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                self.validation_summary(analysis_quarter),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
