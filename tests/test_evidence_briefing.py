import hashlib
import json
from datetime import UTC, datetime

from opensignal.detection.pipeline import OpenFDAScoringPipeline
from opensignal.evidence.models import DraftBrief, DraftClaim
from opensignal.evidence.pipeline import EvidenceBriefingPipeline
from opensignal.evidence.providers import TemplateBriefProvider
from tests.test_scoring_pipeline import write_curated_fixture


class UnsafeProvider:
    name = "test"
    model = "unsafe-fixture"

    def generate(self, *, drug, event, evidence):  # type: ignore[no-untyped-def]
        return DraftBrief(
            status="generated",
            headline=f"{drug} causes {event}",
            claims=[
                DraftClaim(text="This proves causality.", citation_ids=["invented"])
            ],
            uncertainty="None.",
        )


def write_evidence(path, *, matching: bool = True):  # type: ignore[no-untyped-def]
    value = "DRUG A EVENT X" if matching else "UNRELATED MEDICINE TOPIC"
    path.write_text(
        json.dumps(
            [
                {
                    "document_id": "fda-1",
                    "title": value,
                    "publisher": "FDA",
                    "url": "https://www.fda.gov/example",
                    "content": (
                        f"{value}. Reports warrant review and do not establish "
                        "causality."
                    ),
                }
            ]
        )
    )


def test_template_brief_is_cited_and_does_not_mutate_scores(tmp_path) -> None:
    snapshot_id = "brief-fixture"
    write_curated_fixture(tmp_path, snapshot_id)
    OpenFDAScoringPipeline(tmp_path).run(snapshot_id)
    signals = tmp_path / "analytics/openfda/brief-fixture/signals.jsonl"
    before = hashlib.sha256(signals.read_bytes()).hexdigest()
    evidence = tmp_path / "evidence.json"
    write_evidence(evidence)

    result = EvidenceBriefingPipeline(
        tmp_path,
        TemplateBriefProvider(),
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    ).run(
        snapshot_id,
        drug="drug a",
        event="event x",
        evidence_set=evidence,
    )

    brief = json.loads((tmp_path / result.brief_path).read_text())
    assert result.status == "generated"
    assert brief["claims"][0]["citation_ids"] == ["fda-1"]
    assert brief["citations"][0]["document_id"] == "fda-1"
    assert brief["signal_artifact_sha256"] == before
    assert hashlib.sha256(signals.read_bytes()).hexdigest() == before


def test_no_matching_evidence_abstains(tmp_path) -> None:
    snapshot_id = "brief-empty"
    write_curated_fixture(tmp_path, snapshot_id)
    OpenFDAScoringPipeline(tmp_path).run(snapshot_id)
    evidence = tmp_path / "evidence.json"
    write_evidence(evidence, matching=False)
    result = EvidenceBriefingPipeline(
        tmp_path, TemplateBriefProvider()
    ).run(
        snapshot_id,
        drug="drug a",
        event="event x",
        evidence_set=evidence,
    )
    assert result.status == "abstained"
    assert result.citations == 0


def test_invalid_ai_output_fails_closed(tmp_path) -> None:
    snapshot_id = "brief-unsafe"
    write_curated_fixture(tmp_path, snapshot_id)
    OpenFDAScoringPipeline(tmp_path).run(snapshot_id)
    evidence = tmp_path / "evidence.json"
    write_evidence(evidence)
    result = EvidenceBriefingPipeline(tmp_path, UnsafeProvider()).run(
        snapshot_id,
        drug="drug a",
        event="event x",
        evidence_set=evidence,
    )
    brief = json.loads((tmp_path / result.brief_path).read_text())
    assert result.status == "abstained"
    assert "causal" in brief["abstention_reason"]
    assert brief["claims"] == []

