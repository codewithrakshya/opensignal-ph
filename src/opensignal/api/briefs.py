import json

from fastapi import APIRouter, HTTPException

from opensignal.api.signals import signal_artifact
from opensignal.evidence.models import EvidenceBrief
from opensignal.evidence.pipeline import brief_key

router = APIRouter(prefix="/briefs", tags=["evidence briefs"])


@router.get("/{source}/{snapshot_id}", response_model=EvidenceBrief)
def get_brief(
    source: str,
    snapshot_id: str,
    drug: str,
    event: str,
) -> EvidenceBrief:
    """Return a saved brief; generation is deliberately outside the API."""
    path = (
        signal_artifact(source, snapshot_id).parent
        / "briefs"
        / f"{brief_key(drug, event)}.json"
    )
    if not path.exists():
        raise HTTPException(status_code=404, detail="Evidence brief not found")
    brief = EvidenceBrief.model_validate(json.loads(path.read_text()))
    if (brief.drug, brief.event) != (drug.upper(), event.upper()):
        raise HTTPException(status_code=404, detail="Evidence brief not found")
    return brief

