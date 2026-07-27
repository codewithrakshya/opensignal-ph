from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from opensignal.quality.contracts import QualityCheck, RejectedRecord, SourceLocation


class CDCWastewaterRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    record_id: str
    site: str
    state_territory: str
    source: str
    sample_id: str
    sample_collect_date: date
    pcr_target: str
    date_updated: datetime
    county_fips: str | None = None
    population_served: int | None = Field(default=None, gt=0)
    pcr_target_avg_conc: float | None = Field(default=None, ge=0)
    pcr_target_units: str | None = None
    pcr_target_detect: str | None = None

    @field_validator(
        "record_id",
        "site",
        "state_territory",
        "source",
        "sample_id",
        "pcr_target",
    )
    @classmethod
    def required_text_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required text cannot be blank")
        return value


class ValidatedWastewaterRecord(BaseModel):
    source: str = "cdc-wastewater"
    snapshot_id: str
    location: SourceLocation
    record: CDCWastewaterRecord


class CuratedWastewaterObservation(BaseModel):
    source: str = "cdc-wastewater"
    snapshot_id: str
    record_id: str
    site_id: str
    state_territory: str
    reporting_source: str
    county_fips: str | None
    population_served: int | None
    sample_id: str
    sample_collect_date: date
    pathogen: str
    concentration: float | None
    concentration_units: str | None
    target_detected: bool | None
    source_updated_at: datetime
    source_location: SourceLocation


class WastewaterQualityMetrics(BaseModel):
    input_records: int
    schema_valid_records: int
    rejected_records: int
    required_field_completeness: dict[str, float]
    superseded_records_removed: int
    exact_duplicates_removed: int
    accepted_records: int
    curated_observations: int
    unique_sites: int
    states_and_territories: int
    missing_concentration_records: int
    newest_sample_date: date | None
    snapshot_age_days: int | None


class WastewaterQualityReport(BaseModel):
    report_version: int = 1
    source: str = "cdc-wastewater"
    snapshot_id: str
    generated_at: datetime
    metrics: WastewaterQualityMetrics
    checks: list[QualityCheck]
    artifacts: dict[str, str]
    interpretation_notes: list[str]


__all__ = [
    "CDCWastewaterRecord",
    "CuratedWastewaterObservation",
    "RejectedRecord",
    "ValidatedWastewaterRecord",
    "WastewaterQualityMetrics",
    "WastewaterQualityReport",
]
