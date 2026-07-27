import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from opensignal.ingestion.storage import atomic_write, canonical_json_bytes
from opensignal.quality.contracts import (
    CuratedDrugEvent,
    OpenFDAReport,
    QualityCheck,
    QualityMetrics,
    QualityReport,
    RejectedRecord,
    SourceLocation,
    ValidatedReport,
    report_identifier,
)
from opensignal.quality.normalization import (
    normalize_drug_name,
    normalize_drug_role,
    normalize_patient_age,
    normalize_patient_sex,
    normalize_term,
)


@dataclass(frozen=True)
class ProcessingResult:
    accepted_reports: int
    rejected_records: int
    curated_rows: int
    quality_report_path: str


@dataclass(frozen=True)
class Candidate:
    report: OpenFDAReport
    location: SourceLocation


def jsonl_bytes(models: Iterable[Any]) -> bytes:
    lines = [
        json.dumps(
            model.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        for model in models
    ]
    return (("\n".join(lines) + "\n") if lines else "").encode()


class OpenFDAQualityProcessor:
    """Validate and curate an immutable openFDA snapshot."""

    source = "openfda"

    def __init__(
        self,
        data_dir: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.clock = clock or (lambda: datetime.now(UTC))

    def process(self, snapshot_id: str) -> ProcessingResult:
        raw_dir = self.data_dir / "raw" / self.source / snapshot_id
        pages = sorted(raw_dir.glob("page-*.json"))
        if not pages:
            raise FileNotFoundError(f"No raw pages found under {raw_dir}")

        candidates: list[Candidate] = []
        rejected: list[RejectedRecord] = []
        input_records = 0
        completeness_counts = {
            "safetyreportid": 0,
            "receivedate": 0,
            "patient": 0,
            "patient.drug": 0,
            "patient.reaction": 0,
        }

        for page in pages:
            envelope: dict[str, Any] = json.loads(page.read_text(encoding="utf-8"))
            results = envelope.get("response", {}).get("results")
            if not isinstance(results, list):
                raise ValueError(f"Raw page {page} has no response.results list")
            for index, payload in enumerate(results):
                input_records += 1
                self._count_completeness(payload, completeness_counts)
                location = SourceLocation(
                    page=str(page.relative_to(self.data_dir)),
                    index=index,
                )
                try:
                    report = OpenFDAReport.model_validate(payload)
                except ValidationError as error:
                    rejected.append(
                        RejectedRecord(
                            snapshot_id=snapshot_id,
                            location=location,
                            report_id=report_identifier(payload),
                            reasons=self._validation_reasons(error),
                            raw_sha256=self._payload_digest(payload),
                        )
                    )
                    continue
                candidates.append(Candidate(report=report, location=location))

        selected, followups_removed, duplicates_removed = self._latest_reports(
            candidates
        )
        validated: list[ValidatedReport] = []
        curated: list[CuratedDrugEvent] = []
        fallback_count = 0

        for candidate in selected:
            rows, used_fallback = self._curate(candidate, snapshot_id)
            if not rows:
                rejected.append(
                    RejectedRecord(
                        snapshot_id=snapshot_id,
                        location=candidate.location,
                        report_id=candidate.report.safetyreportid,
                        reasons=["No usable normalized drug-event pairs"],
                        raw_sha256=self._payload_digest(
                            candidate.report.model_dump(mode="json")
                        ),
                    )
                )
                continue
            validated.append(
                ValidatedReport(
                    snapshot_id=snapshot_id,
                    location=candidate.location,
                    report=candidate.report,
                )
            )
            curated.extend(rows)
            fallback_count += used_fallback

        generated_at = self.clock()
        artifacts = self._artifact_paths(snapshot_id)
        metrics = self._metrics(
            input_records=input_records,
            schema_valid_records=len(candidates),
            rejected_records=len(rejected),
            completeness_counts=completeness_counts,
            followups_removed=followups_removed,
            duplicates_removed=duplicates_removed,
            validated=validated,
            curated=curated,
            fallback_count=fallback_count,
            generated_at=generated_at,
        )
        quality_report = QualityReport(
            source=self.source,
            snapshot_id=snapshot_id,
            generated_at=generated_at,
            metrics=metrics,
            checks=self._checks(metrics),
            artifacts={
                name: str(path.relative_to(self.data_dir))
                for name, path in artifacts.items()
            },
        )

        atomic_write(artifacts["accepted"], jsonl_bytes(validated))
        atomic_write(artifacts["rejected"], jsonl_bytes(rejected))
        atomic_write(artifacts["curated"], jsonl_bytes(curated))
        atomic_write(
            artifacts["quality_report"],
            canonical_json_bytes(quality_report.model_dump(mode="json")),
        )
        return ProcessingResult(
            accepted_reports=len(validated),
            rejected_records=len(rejected),
            curated_rows=len(curated),
            quality_report_path=str(
                artifacts["quality_report"].relative_to(self.data_dir)
            ),
        )

    @staticmethod
    def _latest_reports(
        candidates: list[Candidate],
    ) -> tuple[list[Candidate], int, int]:
        latest: dict[str, Candidate] = {}
        followups_removed = 0
        duplicates_removed = 0
        for candidate in candidates:
            report_id = candidate.report.safetyreportid
            current = latest.get(report_id)
            if current is None:
                latest[report_id] = candidate
            elif (
                candidate.report.safetyreportversion
                > current.report.safetyreportversion
            ):
                latest[report_id] = candidate
                followups_removed += 1
            elif (
                candidate.report.safetyreportversion
                < current.report.safetyreportversion
            ):
                followups_removed += 1
            else:
                duplicates_removed += 1
        return sorted(
            latest.values(),
            key=lambda item: (
                item.report.safetyreportid,
                item.report.safetyreportversion,
            ),
        ), followups_removed, duplicates_removed

    def _curate(
        self,
        candidate: Candidate,
        snapshot_id: str,
    ) -> tuple[list[CuratedDrugEvent], int]:
        report = candidate.report
        received_date = datetime.strptime(report.receivedate, "%Y%m%d").date()
        reactions = sorted(
            {normalize_term(item.reactionmeddrapt) for item in report.patient.reaction}
        )
        rows: list[CuratedDrugEvent] = []
        age_years, age_group = normalize_patient_age(
            report.patient.patientonsetage,
            report.patient.patientonsetageunit,
        )
        patient_sex = normalize_patient_sex(report.patient.patientsex)
        fallback_count = 0
        seen: set[tuple[str, str, str]] = set()

        for drug in report.patient.drug:
            drug_name, name_source = normalize_drug_name(drug)
            if drug_name is None:
                continue
            if name_source == "reported_medicinal_product":
                fallback_count += 1
            role = normalize_drug_role(drug.drugcharacterization)
            for reaction in reactions:
                pair = (drug_name, role, reaction)
                if pair in seen:
                    continue
                seen.add(pair)
                rows.append(
                    CuratedDrugEvent(
                        snapshot_id=snapshot_id,
                        report_id=report.safetyreportid,
                        report_version=report.safetyreportversion,
                        received_date=received_date,
                        serious=self._serious(report.serious),
                        patient_age_years=age_years,
                        patient_age_group=age_group,
                        patient_sex=patient_sex,
                        drug_name=drug_name,
                        drug_name_source=name_source,
                        drug_role=role,
                        reaction=reaction,
                        source_location=candidate.location,
                    )
                )
        return rows, fallback_count

    def _artifact_paths(self, snapshot_id: str) -> dict[str, Path]:
        return {
            "accepted": self.data_dir
            / "validated"
            / self.source
            / snapshot_id
            / "accepted.jsonl",
            "rejected": self.data_dir
            / "validated"
            / self.source
            / snapshot_id
            / "rejected.jsonl",
            "curated": self.data_dir
            / "curated"
            / self.source
            / snapshot_id
            / "drug_event_pairs.jsonl",
            "quality_report": self.data_dir
            / "quality"
            / self.source
            / snapshot_id
            / "report.json",
        }

    @staticmethod
    def _metrics(
        *,
        input_records: int,
        schema_valid_records: int,
        rejected_records: int,
        completeness_counts: dict[str, int],
        followups_removed: int,
        duplicates_removed: int,
        validated: list[ValidatedReport],
        curated: list[CuratedDrugEvent],
        fallback_count: int,
        generated_at: datetime,
    ) -> QualityMetrics:
        dates = [item.report.receivedate for item in validated]
        newest = (
            max(datetime.strptime(value, "%Y%m%d").date() for value in dates)
            if dates
            else None
        )
        return QualityMetrics(
            input_records=input_records,
            schema_valid_records=schema_valid_records,
            rejected_records=rejected_records,
            required_field_completeness={
                name: round(count / input_records, 4) if input_records else 0
                for name, count in completeness_counts.items()
            },
            followup_records_removed=followups_removed,
            exact_duplicates_removed=duplicates_removed,
            accepted_reports=len(validated),
            curated_drug_event_rows=len(curated),
            unique_drugs=len({row.drug_name for row in curated}),
            unique_reactions=len({row.reaction for row in curated}),
            drug_name_fallbacks=fallback_count,
            newest_received_date=newest,
            snapshot_age_days=(generated_at.date() - newest).days if newest else None,
        )

    @staticmethod
    def _checks(metrics: QualityMetrics) -> list[QualityCheck]:
        validity_rate = (
            metrics.schema_valid_records / metrics.input_records
            if metrics.input_records
            else 0
        )
        minimum_completeness = min(
            metrics.required_field_completeness.values(),
            default=0,
        )
        return [
            QualityCheck(
                name="non_empty_input",
                status="pass" if metrics.input_records > 0 else "fail",
                observed=metrics.input_records,
                threshold="> 0",
                message="At least one source record is required.",
            ),
            QualityCheck(
                name="schema_validity_rate",
                status="pass" if validity_rate >= 0.95 else "warn",
                observed=round(validity_rate, 4),
                threshold=">= 0.95",
                message="Share of source records satisfying the typed contract.",
            ),
            QualityCheck(
                name="required_field_completeness",
                status="pass" if minimum_completeness >= 0.95 else "warn",
                observed=minimum_completeness,
                threshold=">= 0.95 for every required field",
                message="Minimum observed completeness across required fields.",
            ),
            QualityCheck(
                name="curated_output",
                status="pass" if metrics.curated_drug_event_rows > 0 else "fail",
                observed=metrics.curated_drug_event_rows,
                threshold="> 0",
                message="At least one normalized drug-event pair is required.",
            ),
            QualityCheck(
                name="snapshot_freshness",
                status="observed",
                observed=metrics.snapshot_age_days,
                message=(
                    "Age is reported for context; acceptable freshness depends "
                    "on the manifest's analytical purpose."
                ),
            ),
        ]

    @staticmethod
    def _validation_reasons(error: ValidationError) -> list[str]:
        reasons = []
        for item in error.errors(include_url=False):
            location = ".".join(str(part) for part in item["loc"])
            reasons.append(f"{location}: {item['msg']}")
        return reasons

    @staticmethod
    def _count_completeness(
        payload: Any,
        counts: dict[str, int],
    ) -> None:
        if not isinstance(payload, dict):
            return
        if payload.get("safetyreportid") not in (None, ""):
            counts["safetyreportid"] += 1
        if payload.get("receivedate") not in (None, ""):
            counts["receivedate"] += 1
        patient = payload.get("patient")
        if not isinstance(patient, dict):
            return
        counts["patient"] += 1
        if patient.get("drug"):
            counts["patient.drug"] += 1
        if patient.get("reaction"):
            counts["patient.reaction"] += 1

    @staticmethod
    def _payload_digest(payload: Any) -> str:
        content = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode()
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _serious(value: str | None) -> bool | None:
        if value == "1":
            return True
        if value == "2":
            return False
        return None
