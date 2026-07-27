from fastapi.testclient import TestClient

from opensignal.api.main import app
from opensignal.core.config import get_settings


def test_readiness_and_metrics(tmp_path) -> None:
    get_settings().data_dir = tmp_path
    client = TestClient(app)
    ready = client.get("/ready")
    metrics = client.get("/metrics")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert "opensignal_http_requests_total" in metrics.text
    assert ready.headers["x-request-id"]


def test_review_requires_role_and_writes_chained_audit(tmp_path) -> None:
    get_settings().data_dir = tmp_path
    client = TestClient(app)
    payload = {
        "drug": "drug a",
        "event": "event x",
        "decision": "escalate",
        "rationale": "The signal needs manual clinical review.",
    }
    denied = client.post("/reviews/openfda/snapshot-1", json=payload)
    accepted = client.post(
        "/reviews/openfda/snapshot-1",
        json=payload,
        headers={
            "x-opensignal-role": "reviewer",
            "x-opensignal-actor": "reviewer@example.org",
        },
    )
    assert denied.status_code == 403
    assert accepted.status_code == 201
    assert accepted.json()["role"] == "reviewer"
    assert (tmp_path / "audit/openfda/snapshot-1.jsonl").exists()
