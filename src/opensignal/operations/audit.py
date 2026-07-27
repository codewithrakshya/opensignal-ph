import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from opensignal.ingestion.storage import atomic_write


class ReviewAction(BaseModel):
    drug: str
    event: str
    decision: Literal["triage", "monitor", "dismiss", "escalate"]
    rationale: str = Field(min_length=10, max_length=2_000)


class AuditEvent(BaseModel):
    event_id: str
    occurred_at: datetime
    actor: str
    role: Literal["reviewer", "admin"]
    action: str
    source: str
    snapshot_id: str
    drug: str
    event: str
    decision: str
    rationale: str
    previous_digest: str | None


def append_review_event(
    path: Path,
    *,
    actor: str,
    role: Literal["reviewer", "admin"],
    source: str,
    snapshot_id: str,
    action: ReviewAction,
) -> AuditEvent:
    existing = path.read_bytes() if path.exists() else b""
    previous_digest = hashlib.sha256(existing).hexdigest() if existing else None
    occurred_at = datetime.now(UTC)
    identity = (
        f"{occurred_at.isoformat()}\0{actor}\0{source}\0{snapshot_id}\0"
        f"{action.drug.upper()}\0{action.event.upper()}\0{action.decision}"
    )
    event = AuditEvent(
        event_id=hashlib.sha256(identity.encode()).hexdigest()[:24],
        occurred_at=occurred_at,
        actor=actor,
        role=role,
        action="signal_reviewed",
        source=source,
        snapshot_id=snapshot_id,
        drug=action.drug.upper(),
        event=action.event.upper(),
        decision=action.decision,
        rationale=action.rationale,
        previous_digest=previous_digest,
    )
    line = json.dumps(
        event.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode() + b"\n"
    atomic_write(path, existing + line)
    return event

