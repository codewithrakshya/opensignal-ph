import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from opensignal.core.config import get_settings
from opensignal.ingestion.manifest import SAFE_ID
from opensignal.temporal.models import TemporalSignal

router = APIRouter(prefix="/temporal-signals", tags=["signals"])


def temporal_artifact(source: str, snapshot_id: str) -> Path:
    if not SAFE_ID.fullmatch(source) or not SAFE_ID.fullmatch(snapshot_id):
        raise HTTPException(status_code=400, detail="Invalid source or snapshot ID")
    return (
        get_settings().data_dir
        / "analytics"
        / source
        / snapshot_id
        / "temporal"
        / "signals.jsonl"
    )


@router.get("/{source}/{snapshot_id}", response_model=list[TemporalSignal])
def list_temporal_signals(
    source: str,
    snapshot_id: str,
    drug: str | None = None,
    event: str | None = None,
    anomalies_only: bool = False,
    changes_only: bool = False,
    limit: int = Query(default=100, ge=1, le=1_000),
) -> list[TemporalSignal]:
    path = temporal_artifact(source, snapshot_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Temporal artifact not found")
    results: list[TemporalSignal] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        score = TemporalSignal.model_validate(json.loads(line))
        if drug and score.drug != drug.upper():
            continue
        if event and score.event != event.upper():
            continue
        if anomalies_only and not score.is_anomaly:
            continue
        if changes_only and not score.is_change_point:
            continue
        results.append(score)
        if len(results) == limit:
            break
    return results
