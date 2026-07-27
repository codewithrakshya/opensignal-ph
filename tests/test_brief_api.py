from fastapi.testclient import TestClient

from opensignal.api.main import app
from opensignal.core.config import get_settings
from opensignal.detection.pipeline import OpenFDAScoringPipeline
from opensignal.evidence.pipeline import EvidenceBriefingPipeline
from opensignal.evidence.providers import TemplateBriefProvider
from tests.test_evidence_briefing import write_evidence
from tests.test_scoring_pipeline import write_curated_fixture


def test_brief_api_returns_saved_artifact(tmp_path) -> None:
    snapshot_id = "brief-api"
    write_curated_fixture(tmp_path, snapshot_id)
    OpenFDAScoringPipeline(tmp_path).run(snapshot_id)
    evidence = tmp_path / "evidence.json"
    write_evidence(evidence)
    EvidenceBriefingPipeline(tmp_path, TemplateBriefProvider()).run(
        snapshot_id,
        drug="drug a",
        event="event x",
        evidence_set=evidence,
    )
    get_settings().data_dir = tmp_path

    response = TestClient(app).get(
        f"/briefs/openfda/{snapshot_id}",
        params={"drug": "drug a", "event": "event x"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "generated"
