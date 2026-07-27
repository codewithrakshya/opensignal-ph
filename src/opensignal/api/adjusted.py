import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from opensignal.adjusted.models import SensitivityResult
from opensignal.api.signals import signal_artifact

router = APIRouter(prefix="/adjusted", tags=["adjusted associations"])


def adjusted_artifact(source: str, snapshot_id: str) -> Path:
    return (
        signal_artifact(source, snapshot_id).parent
        / "adjusted"
        / "sensitivity.jsonl"
    )


@router.get("/{source}/{snapshot_id}", response_model=list[SensitivityResult])
def list_adjusted(
    source: str,
    snapshot_id: str,
    drug: str | None = None,
    event: str | None = None,
    limit: int = Query(default=100, ge=1, le=1_000),
) -> list[SensitivityResult]:
    path = adjusted_artifact(source, snapshot_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Adjusted artifact not found")
    output: list[SensitivityResult] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        result = SensitivityResult.model_validate(json.loads(line))
        if drug and result.drug != drug.upper():
            continue
        if event and result.event != event.upper():
            continue
        output.append(result)
        if len(output) == limit:
            break
    return output
