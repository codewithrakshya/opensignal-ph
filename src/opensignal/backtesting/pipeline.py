import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from opensignal.backtesting.evaluator import DETECTORS, evaluate
from opensignal.backtesting.models import BacktestMetadata
from opensignal.backtesting.reference import load_reference_set
from opensignal.ingestion.storage import atomic_write, canonical_json_bytes
from opensignal.temporal.models import TemporalFeature


@dataclass(frozen=True)
class BacktestResult:
    snapshot_id: str
    reference_set_id: str
    ranking_rows: int
    metric_rows: int
    summary_path: str
    rankings_path: str
    quarter_metrics_path: str
    metadata_path: str


def jsonl_bytes(rows: Iterable[BaseModel]) -> bytes:
    lines = [
        json.dumps(row.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        for row in rows
    ]
    return (("\n".join(lines) + "\n") if lines else "").encode()


class BacktestPipeline:
    def __init__(
        self,
        data_dir: Path,
        *,
        k: int = 10,
        random_state: int = 42,
        minimum_training_rows: int = 8,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if k < 1:
            raise ValueError("k must be positive")
        self.data_dir = data_dir
        self.k = k
        self.random_state = random_state
        self.minimum_training_rows = minimum_training_rows
        self.clock = clock or (lambda: datetime.now(UTC))

    def run(self, snapshot_id: str, reference_path: Path) -> BacktestResult:
        feature_path = (
            self.data_dir
            / "analytics"
            / "openfda"
            / snapshot_id
            / "temporal"
            / "features.jsonl"
        )
        if not feature_path.exists():
            raise FileNotFoundError(f"Temporal features not found: {feature_path}")
        feature_content = feature_path.read_bytes()
        reference_content = reference_path.read_bytes()
        features = [
            TemporalFeature.model_validate(json.loads(line))
            for line in feature_content.splitlines()
            if line
        ]
        reference_set = load_reference_set(reference_path)
        evaluation = evaluate(
            features,
            reference_set,
            snapshot_id=snapshot_id,
            generated_at=self.clock(),
            k=self.k,
            random_state=self.random_state,
            minimum_training_rows=self.minimum_training_rows,
        )
        output_dir = (
            self.data_dir
            / "analytics"
            / "openfda"
            / snapshot_id
            / "backtests"
            / reference_set.reference_set_id
        )
        rankings_path = output_dir / "rankings.jsonl"
        metrics_path = output_dir / "quarter_metrics.jsonl"
        summary_path = output_dir / "summary.json"
        metadata_path = output_dir / "metadata.json"
        metadata = BacktestMetadata(
            snapshot_id=snapshot_id,
            reference_set_id=reference_set.reference_set_id,
            feature_input_path=str(feature_path.relative_to(self.data_dir)),
            feature_input_sha256=hashlib.sha256(feature_content).hexdigest(),
            reference_input_path=str(reference_path),
            reference_input_sha256=hashlib.sha256(reference_content).hexdigest(),
            detectors=list(DETECTORS),
            k=self.k,
            random_state=self.random_state,
            minimum_training_rows=self.minimum_training_rows,
        )
        atomic_write(rankings_path, jsonl_bytes(evaluation.rankings))
        atomic_write(metrics_path, jsonl_bytes(evaluation.quarter_metrics))
        atomic_write(
            summary_path,
            canonical_json_bytes(evaluation.summary.model_dump(mode="json")),
        )
        atomic_write(
            metadata_path,
            canonical_json_bytes(metadata.model_dump(mode="json")),
        )
        return BacktestResult(
            snapshot_id=snapshot_id,
            reference_set_id=reference_set.reference_set_id,
            ranking_rows=len(evaluation.rankings),
            metric_rows=len(evaluation.quarter_metrics),
            summary_path=str(summary_path.relative_to(self.data_dir)),
            rankings_path=str(rankings_path.relative_to(self.data_dir)),
            quarter_metrics_path=str(metrics_path.relative_to(self.data_dir)),
            metadata_path=str(metadata_path.relative_to(self.data_dir)),
        )
