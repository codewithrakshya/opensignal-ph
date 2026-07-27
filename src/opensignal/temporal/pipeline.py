import hashlib
import json
import pickle
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from opensignal.ingestion.storage import atomic_write, canonical_json_bytes
from opensignal.temporal.detector import FEATURE_NAMES, fit_temporal_detector
from opensignal.temporal.features import (
    TemporalObservation,
    build_temporal_features,
)
from opensignal.temporal.models import TemporalRunMetadata


@dataclass(frozen=True)
class TemporalResult:
    snapshot_id: str
    feature_rows: int
    signal_rows: int
    anomalies: int
    change_points: int
    features_path: str
    signals_path: str
    metadata_path: str
    model_path: str


def jsonl_bytes(rows: Iterable[BaseModel]) -> bytes:
    lines = [
        json.dumps(row.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        for row in rows
    ]
    return (("\n".join(lines) + "\n") if lines else "").encode()


class OpenFDATemporalPipeline:
    source = "openfda"

    def __init__(
        self,
        data_dir: Path,
        *,
        contamination: float = 0.05,
        random_state: int = 42,
        minimum_history: int = 4,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not 0 < contamination <= 0.5:
            raise ValueError("contamination must be in (0, 0.5]")
        self.data_dir = data_dir
        self.contamination = contamination
        self.random_state = random_state
        self.minimum_history = minimum_history
        self.clock = clock or (lambda: datetime.now(UTC))

    def run(self, snapshot_id: str) -> TemporalResult:
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
        features = build_temporal_features(self._load_observations(content))
        model_artifact, signals = fit_temporal_detector(
            features,
            contamination=self.contamination,
            random_state=self.random_state,
            minimum_history=self.minimum_history,
        )
        output_dir = (
            self.data_dir / "analytics" / self.source / snapshot_id / "temporal"
        )
        features_path = output_dir / "features.jsonl"
        signals_path = output_dir / "signals.jsonl"
        model_path = output_dir / "model.pkl"
        metadata_path = output_dir / "metadata.json"
        feature_content = jsonl_bytes(features)
        signal_content = jsonl_bytes(signals)
        model_content = pickle.dumps(model_artifact, protocol=5)
        metadata = TemporalRunMetadata(
            snapshot_id=snapshot_id,
            generated_at=self.clock(),
            curated_input_path=str(curated_path.relative_to(self.data_dir)),
            curated_input_sha256=hashlib.sha256(content).hexdigest(),
            random_state=self.random_state,
            contamination=self.contamination,
            minimum_history_quarters=self.minimum_history,
            feature_names=FEATURE_NAMES,
            feature_rows=len(features),
            signal_rows=len(signals),
            model_input_sha256=hashlib.sha256(feature_content).hexdigest(),
            model_artifact_path=str(model_path.relative_to(self.data_dir)),
            model_artifact_sha256=hashlib.sha256(model_content).hexdigest(),
        )
        atomic_write(features_path, feature_content)
        atomic_write(signals_path, signal_content)
        atomic_write(model_path, model_content)
        atomic_write(
            metadata_path,
            canonical_json_bytes(metadata.model_dump(mode="json")),
        )
        return TemporalResult(
            snapshot_id=snapshot_id,
            feature_rows=len(features),
            signal_rows=len(signals),
            anomalies=sum(row.is_anomaly for row in signals),
            change_points=sum(row.is_change_point for row in signals),
            features_path=str(features_path.relative_to(self.data_dir)),
            signals_path=str(signals_path.relative_to(self.data_dir)),
            metadata_path=str(metadata_path.relative_to(self.data_dir)),
            model_path=str(model_path.relative_to(self.data_dir)),
        )

    @staticmethod
    def _load_observations(content: bytes) -> list[TemporalObservation]:
        observations: list[TemporalObservation] = []
        for line_number, line in enumerate(content.splitlines(), start=1):
            if not line:
                continue
            payload: dict[str, Any] = json.loads(line)
            try:
                observations.append(
                    TemporalObservation(
                        report_id=str(payload["report_id"]),
                        received_date=datetime.strptime(
                            str(payload["received_date"]), "%Y-%m-%d"
                        ).date(),
                        drug=str(payload["drug_name"]),
                        event=str(payload["reaction"]),
                        serious=payload.get("serious"),
                    )
                )
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid curated row at line {line_number}"
                ) from error
        return observations
