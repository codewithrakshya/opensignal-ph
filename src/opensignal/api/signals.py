import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from opensignal.core.config import get_settings
from opensignal.core.models import SignalScore
from opensignal.ingestion.manifest import SAFE_ID

router = APIRouter(prefix="/signals", tags=["signals"])


def signal_artifact(source: str, snapshot_id: str) -> Path:
    if not SAFE_ID.fullmatch(source) or not SAFE_ID.fullmatch(snapshot_id):
        raise HTTPException(status_code=400, detail="Invalid source or snapshot ID")
    return (
        get_settings().data_dir
        / "analytics"
        / source
        / snapshot_id
        / "signals.jsonl"
    )


@router.get("/{source}/{snapshot_id}", response_model=list[SignalScore])
def list_signals(
    source: str,
    snapshot_id: str,
    detector: str | None = None,
    drug: str | None = None,
    event: str | None = None,
    potential_only: bool = False,
    stable_only: bool = False,
    limit: int = Query(default=100, ge=1, le=1_000),
) -> list[SignalScore]:
    """Return auditable signal scores from a versioned analytics artifact."""
    path = signal_artifact(source, snapshot_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Signal artifact not found")

    results: list[SignalScore] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        score = SignalScore.model_validate(json.loads(line))
        if detector and score.detector != detector:
            continue
        if drug and score.drug != drug.upper():
            continue
        if event and score.event != event.upper():
            continue
        if potential_only and not score.is_potential_signal:
            continue
        if stable_only and not score.passes_stability_rule:
            continue
        results.append(score)
        if len(results) == limit:
            break
    return results
