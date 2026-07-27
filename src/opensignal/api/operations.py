from typing import Literal

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel

from opensignal.core.config import get_settings
from opensignal.operations.audit import AuditEvent, ReviewAction, append_review_event
from opensignal.operations.observability import prometheus_metrics

router = APIRouter(tags=["operations"])


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    data_directory: str


@router.get("/ready", response_model=ReadinessResponse)
def readiness() -> ReadinessResponse:
    data_dir = get_settings().data_dir
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        probe = data_dir / ".readiness"
        probe.touch()
        probe.unlink()
    except OSError as error:
        raise HTTPException(
            status_code=503, detail="Artifact storage is not writable"
        ) from error
    return ReadinessResponse(status="ready", data_directory=str(data_dir))


@router.get("/metrics", response_class=Response)
def metrics() -> Response:
    return Response(prometheus_metrics(), media_type="text/plain")


@router.post(
    "/reviews/{source}/{snapshot_id}",
    response_model=AuditEvent,
    status_code=201,
)
def review_signal(
    source: str,
    snapshot_id: str,
    action: ReviewAction,
    x_opensignal_actor: str = Header(default="anonymous"),
    x_opensignal_role: str = Header(default="viewer"),
) -> AuditEvent:
    if x_opensignal_role not in {"reviewer", "admin"}:
        raise HTTPException(status_code=403, detail="Reviewer role required")
    role: Literal["reviewer", "admin"] = (
        "admin" if x_opensignal_role == "admin" else "reviewer"
    )
    path = (
        get_settings().data_dir
        / "audit"
        / source
        / f"{snapshot_id}.jsonl"
    )
    return append_review_event(
        path,
        actor=x_opensignal_actor,
        role=role,
        source=source,
        snapshot_id=snapshot_id,
        action=action,
    )

