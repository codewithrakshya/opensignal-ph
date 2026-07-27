import re
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

FDA_DATE = re.compile(r"^\d{8}$")


class OpenFDAConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    generic_name: list[str] = Field(default_factory=list)
    brand_name: list[str] = Field(default_factory=list)
    substance_name: list[str] = Field(default_factory=list)


class OpenFDADrug(BaseModel):
    model_config = ConfigDict(extra="ignore")

    medicinalproduct: str | None = None
    drugcharacterization: str | None = None
    openfda: OpenFDAConfig = Field(default_factory=OpenFDAConfig)


class OpenFDAReaction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reactionmeddrapt: str

    @field_validator("reactionmeddrapt")
    @classmethod
    def reaction_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reactionmeddrapt cannot be blank")
        return value


class OpenFDAPatient(BaseModel):
    model_config = ConfigDict(extra="ignore")

    patientonsetage: str | None = None
    patientonsetageunit: str | None = None
    patientsex: str | None = None
    reaction: list[OpenFDAReaction] = Field(min_length=1)
    drug: list[OpenFDADrug] = Field(min_length=1)


class OpenFDAReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    safetyreportid: str
    safetyreportversion: int = Field(default=1, ge=1)
    receivedate: str
    serious: str | None = None
    patient: OpenFDAPatient

    @field_validator("safetyreportid")
    @classmethod
    def report_id_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("safetyreportid cannot be blank")
        return value

    @field_validator("receivedate")
    @classmethod
    def validate_fda_date(cls, value: str) -> str:
        if not FDA_DATE.fullmatch(value):
            raise ValueError("receivedate must use YYYYMMDD")
        datetime.strptime(value, "%Y%m%d")
        return value


class SourceLocation(BaseModel):
    page: str
    index: int = Field(ge=0)


class ValidatedReport(BaseModel):
    source: str = "openfda"
    snapshot_id: str
    location: SourceLocation
    report: OpenFDAReport


class RejectedRecord(BaseModel):
    source: str = "openfda"
    snapshot_id: str
    location: SourceLocation
    report_id: str | None
    reasons: list[str]
    raw_sha256: str


class CuratedDrugEvent(BaseModel):
    source: str = "openfda"
    snapshot_id: str
    report_id: str
    report_version: int
    received_date: date
    serious: bool | None
    patient_age_years: float | None = Field(default=None, ge=0, le=130)
    patient_age_group: str = "unknown"
    patient_sex: str = "unknown"
    drug_name: str
    drug_name_source: str
    drug_role: str
    reaction: str
    source_location: SourceLocation


class QualityCheck(BaseModel):
    name: str
    status: str
    observed: float | int | str | None
    threshold: str | None = None
    message: str


class QualityMetrics(BaseModel):
    input_records: int
    schema_valid_records: int
    rejected_records: int
    required_field_completeness: dict[str, float]
    followup_records_removed: int
    exact_duplicates_removed: int
    accepted_reports: int
    curated_drug_event_rows: int
    unique_drugs: int
    unique_reactions: int
    drug_name_fallbacks: int
    newest_received_date: date | None
    snapshot_age_days: int | None


class QualityReport(BaseModel):
    report_version: int = 1
    source: str
    snapshot_id: str
    generated_at: datetime
    metrics: QualityMetrics
    checks: list[QualityCheck]
    artifacts: dict[str, str]


def report_identifier(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("safetyreportid")
    return str(value) if value is not None else None
