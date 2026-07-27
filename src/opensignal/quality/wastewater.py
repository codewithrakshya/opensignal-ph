import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from opensignal.ingestion.storage import atomic_write, canonical_json_bytes
from opensignal.quality.contracts import QualityCheck, RejectedRecord, SourceLocation
from opensignal.quality.normalization import normalize_term
from opensignal.quality.processor import ProcessingResult, jsonl_bytes
from opensignal.quality.wastewater_contracts import (
    CDCWastewaterRecord,
    CuratedWastewaterObservation,
    ValidatedWastewaterRecord,
    WastewaterQualityMetrics,
    WastewaterQualityReport,
)


@dataclass(frozen=True)
class WastewaterCandidate:
    record: CDCWastewaterRecord
    location: SourceLocation


class CDCWastewaterQualityProcessor:
    source = "cdc-wastewater"

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

        candidates: list[WastewaterCandidate] = []
        rejected: list[RejectedRecord] = []
        input_records = 0
        completeness_counts = {
            "record_id": 0,
            "site": 0,
            "state_territory": 0,
            "sample_id": 0,
            "sample_collect_date": 0,
            "pcr_target": 0,
            "date_updated": 0,
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
                    record = CDCWastewaterRecord.model_validate(payload)
                except ValidationError as error:
                    rejected.append(
                        RejectedRecord(
                            source=self.source,
                            snapshot_id=snapshot_id,
                            location=location,
                            report_id=self._record_identifier(payload),
                            reasons=self._validation_reasons(error),
                            raw_sha256=self._payload_digest(payload),
                        )
                    )
                    continue
                candidates.append(WastewaterCandidate(record, location))

        selected, superseded, duplicates = self._latest_records(candidates)
        validated = [
            ValidatedWastewaterRecord(
                snapshot_id=snapshot_id,
                location=item.location,
                record=item.record,
            )
            for item in selected
        ]
        curated = [self._curate(item, snapshot_id) for item in selected]
        generated_at = self.clock()
        artifacts = self._artifact_paths(snapshot_id)
        metrics = self._metrics(
            input_records=input_records,
            schema_valid_records=len(candidates),
            rejected_records=len(rejected),
            completeness_counts=completeness_counts,
            superseded=superseded,
            duplicates=duplicates,
            curated=curated,
            generated_at=generated_at,
        )
        report = WastewaterQualityReport(
            snapshot_id=snapshot_id,
            generated_at=generated_at,
            metrics=metrics,
            checks=self._checks(metrics),
            artifacts={
                name: str(path.relative_to(self.data_dir))
                for name, path in artifacts.items()
            },
            interpretation_notes=[
                "Wastewater concentrations should not be compared directly "
                "across sampling locations because collection frequencies and "
                "laboratory methods may differ.",
                "Missing concentration may coexist with a valid non-detect record.",
            ],
        )

        atomic_write(artifacts["accepted"], jsonl_bytes(validated))
        atomic_write(artifacts["rejected"], jsonl_bytes(rejected))
        atomic_write(artifacts["curated"], jsonl_bytes(curated))
        atomic_write(
            artifacts["quality_report"],
            canonical_json_bytes(report.model_dump(mode="json")),
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
    def _latest_records(
        candidates: list[WastewaterCandidate],
    ) -> tuple[list[WastewaterCandidate], int, int]:
        latest: dict[str, WastewaterCandidate] = {}
        superseded = 0
        duplicates = 0
        for candidate in candidates:
            current = latest.get(candidate.record.record_id)
            if current is None:
                latest[candidate.record.record_id] = candidate
            elif candidate.record.date_updated > current.record.date_updated:
                latest[candidate.record.record_id] = candidate
                superseded += 1
            elif candidate.record.date_updated < current.record.date_updated:
                superseded += 1
            else:
                duplicates += 1
        return sorted(
            latest.values(),
            key=lambda item: item.record.record_id,
        ), superseded, duplicates

    @staticmethod
    def _curate(
        candidate: WastewaterCandidate,
        snapshot_id: str,
    ) -> CuratedWastewaterObservation:
        record = candidate.record
        detected = {
            "yes": True,
            "no": False,
        }.get(record.pcr_target_detect.lower() if record.pcr_target_detect else "")
        return CuratedWastewaterObservation(
            snapshot_id=snapshot_id,
            record_id=record.record_id,
            site_id=record.site,
            state_territory=record.state_territory.upper(),
            reporting_source=normalize_term(record.source),
            county_fips=record.county_fips,
            population_served=record.population_served,
            sample_id=record.sample_id,
            sample_collect_date=record.sample_collect_date,
            pathogen=normalize_term(record.pcr_target),
            concentration=record.pcr_target_avg_conc,
            concentration_units=(
                normalize_term(record.pcr_target_units)
                if record.pcr_target_units
                else None
            ),
            target_detected=detected,
            source_updated_at=record.date_updated,
            source_location=candidate.location,
        )

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
            / "observations.jsonl",
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
        superseded: int,
        duplicates: int,
        curated: list[CuratedWastewaterObservation],
        generated_at: datetime,
    ) -> WastewaterQualityMetrics:
        newest = max(
            (item.sample_collect_date for item in curated),
            default=None,
        )
        return WastewaterQualityMetrics(
            input_records=input_records,
            schema_valid_records=schema_valid_records,
            rejected_records=rejected_records,
            required_field_completeness={
                name: round(count / input_records, 4) if input_records else 0
                for name, count in completeness_counts.items()
            },
            superseded_records_removed=superseded,
            exact_duplicates_removed=duplicates,
            accepted_records=len(curated),
            curated_observations=len(curated),
            unique_sites=len({item.site_id for item in curated}),
            states_and_territories=len(
                {item.state_territory for item in curated}
            ),
            missing_concentration_records=sum(
                item.concentration is None for item in curated
            ),
            newest_sample_date=newest,
            snapshot_age_days=(
                (generated_at.date() - newest).days if newest else None
            ),
        )

    @staticmethod
    def _checks(metrics: WastewaterQualityMetrics) -> list[QualityCheck]:
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
                status="pass" if metrics.input_records else "fail",
                observed=metrics.input_records,
                threshold="> 0",
                message="At least one wastewater record is required.",
            ),
            QualityCheck(
                name="schema_validity_rate",
                status="pass" if validity_rate >= 0.95 else "warn",
                observed=round(validity_rate, 4),
                threshold=">= 0.95",
                message="Share of records satisfying the typed CDC contract.",
            ),
            QualityCheck(
                name="required_field_completeness",
                status="pass" if minimum_completeness >= 0.95 else "warn",
                observed=minimum_completeness,
                threshold=">= 0.95 for every required field",
                message="Minimum completeness among required source fields.",
            ),
            QualityCheck(
                name="snapshot_freshness",
                status="observed",
                observed=metrics.snapshot_age_days,
                message="Age of the newest sample at processing time.",
            ),
        ]

    @staticmethod
    def _count_completeness(payload: Any, counts: dict[str, int]) -> None:
        if not isinstance(payload, dict):
            return
        for field in counts:
            if payload.get(field) not in (None, ""):
                counts[field] += 1

    @staticmethod
    def _validation_reasons(error: ValidationError) -> list[str]:
        return [
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors(include_url=False)
        ]

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
    def _record_identifier(payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        value = payload.get("record_id")
        return str(value) if value is not None else None
