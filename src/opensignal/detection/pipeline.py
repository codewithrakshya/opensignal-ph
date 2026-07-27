import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from opensignal.core.models import SignalScore
from opensignal.detection.base import SignalDetector
from opensignal.detection.contingency import (
    ContingencyBuilder,
    DrugEventObservation,
)
from opensignal.detection.prr import ProportionalReportingRatio
from opensignal.detection.ror import ReportingOddsRatio
from opensignal.ingestion.storage import atomic_write, canonical_json_bytes


class ScoringRunMetadata(BaseModel):
    artifact_version: int = 1
    source: str = "openfda"
    snapshot_id: str
    generated_at: datetime
    analysis_date: date
    curated_input_path: str
    curated_input_sha256: str
    unique_reports: int
    candidate_pairs: int
    scores_written: int
    potential_signals: int
    stable_signals: int
    detectors: list[str]
    criteria_version: str = "phase3-v1"


@dataclass(frozen=True)
class ScoringResult:
    snapshot_id: str
    scores_written: int
    potential_signals: int
    stable_signals: int
    signals_path: str
    metadata_path: str


def score_jsonl_bytes(scores: Iterable[SignalScore]) -> bytes:
    lines = [
        json.dumps(
            score.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        for score in scores
    ]
    return (("\n".join(lines) + "\n") if lines else "").encode()


class OpenFDAScoringPipeline:
    source = "openfda"

    def __init__(
        self,
        data_dir: Path,
        *,
        detectors: list[SignalDetector] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.detectors = detectors or [
            ReportingOddsRatio(),
            ProportionalReportingRatio(),
        ]
        self.clock = clock or (lambda: datetime.now(UTC))

    def run(self, snapshot_id: str) -> ScoringResult:
        curated_path = (
            self.data_dir
            / "curated"
            / self.source
            / snapshot_id
            / "drug_event_pairs.jsonl"
        )
        if not curated_path.exists():
            raise FileNotFoundError(f"Curated input not found: {curated_path}")
        content = curated_path.read_bytes()
        observations = self._load_observations(content)
        builder = ContingencyBuilder(observations)

        scores: list[SignalScore] = []
        for drug, event in builder.candidate_pairs():
            table = builder.build(drug, event)
            for detector in self.detectors:
                scores.append(
                    detector.score(
                        drug=drug,
                        event=event,
                        analysis_date=builder.analysis_date,
                        inputs=table,
                    )
                )
        scores.sort(
            key=lambda item: (
                not item.is_potential_signal,
                not item.passes_stability_rule,
                -item.score,
                item.detector,
                item.drug,
                item.event,
            )
        )

        output_dir = self.data_dir / "analytics" / self.source / snapshot_id
        signals_path = output_dir / "signals.jsonl"
        metadata_path = output_dir / "metadata.json"
        potential_signals = sum(item.is_potential_signal for item in scores)
        stable_signals = sum(
            item.is_potential_signal and item.passes_stability_rule
            for item in scores
        )
        metadata = ScoringRunMetadata(
            snapshot_id=snapshot_id,
            generated_at=self.clock(),
            analysis_date=builder.analysis_date,
            curated_input_path=str(curated_path.relative_to(self.data_dir)),
            curated_input_sha256=hashlib.sha256(content).hexdigest(),
            unique_reports=len(builder.all_reports),
            candidate_pairs=len(builder.candidate_pairs()),
            scores_written=len(scores),
            potential_signals=potential_signals,
            stable_signals=stable_signals,
            detectors=[detector.name for detector in self.detectors],
        )
        atomic_write(signals_path, score_jsonl_bytes(scores))
        atomic_write(
            metadata_path,
            canonical_json_bytes(metadata.model_dump(mode="json")),
        )
        return ScoringResult(
            snapshot_id=snapshot_id,
            scores_written=len(scores),
            potential_signals=potential_signals,
            stable_signals=stable_signals,
            signals_path=str(signals_path.relative_to(self.data_dir)),
            metadata_path=str(metadata_path.relative_to(self.data_dir)),
        )

    @staticmethod
    def _load_observations(content: bytes) -> list[DrugEventObservation]:
        observations: list[DrugEventObservation] = []
        for line_number, line in enumerate(content.splitlines(), start=1):
            if not line:
                continue
            payload: dict[str, Any] = json.loads(line)
            try:
                observations.append(
                    DrugEventObservation(
                        report_id=str(payload["report_id"]),
                        received_date=date.fromisoformat(payload["received_date"]),
                        drug=str(payload["drug_name"]),
                        event=str(payload["reaction"]),
                    )
                )
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid curated row at line {line_number}"
                ) from error
        return observations
