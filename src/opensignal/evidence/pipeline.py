import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter

from opensignal.evidence.models import (
    EvidenceBrief,
    EvidenceCitation,
    EvidenceDocument,
)
from opensignal.evidence.providers import BriefProvider
from opensignal.evidence.retrieval import retrieve_evidence
from opensignal.evidence.validation import abstention, validation_errors
from opensignal.ingestion.storage import atomic_write, canonical_json_bytes

DOCUMENTS = TypeAdapter(list[EvidenceDocument])


@dataclass(frozen=True)
class BriefingResult:
    status: str
    brief_path: str
    citations: int


def brief_key(drug: str, event: str) -> str:
    return hashlib.sha256(f"{drug.upper()}\0{event.upper()}".encode()).hexdigest()[:20]


class EvidenceBriefingPipeline:
    source = "openfda"

    def __init__(
        self,
        data_dir: Path,
        provider: BriefProvider,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.provider = provider
        self.clock = clock or (lambda: datetime.now(UTC))

    def run(
        self,
        snapshot_id: str,
        *,
        drug: str,
        event: str,
        evidence_set: Path,
    ) -> BriefingResult:
        signals_path = (
            self.data_dir
            / "analytics"
            / self.source
            / snapshot_id
            / "signals.jsonl"
        )
        signal_bytes = signals_path.read_bytes()
        if not self._signal_exists(signal_bytes, drug, event):
            raise ValueError("Requested drug-event pair is not in the signal artifact")
        evidence_bytes = evidence_set.read_bytes()
        documents = DOCUMENTS.validate_python(json.loads(evidence_bytes))
        retrieved = retrieve_evidence(documents, drug=drug, event=event)
        draft = self.provider.generate(drug=drug, event=event, evidence=retrieved)
        errors = validation_errors(draft, retrieved)
        if errors:
            draft = abstention("; ".join(errors))
        citations = [
            EvidenceCitation(
                citation_id=item.document_id,
                document_id=item.document_id,
                title=item.title,
                publisher=item.publisher,
                url=item.url,
                excerpt=item.excerpt,
            )
            for item in retrieved
            if any(
                item.document_id in claim.citation_ids for claim in draft.claims
            )
        ]
        brief = EvidenceBrief(
            source=self.source,
            snapshot_id=snapshot_id,
            drug=drug.upper(),
            event=event.upper(),
            generated_at=self.clock(),
            status=draft.status,
            headline=draft.headline,
            claims=draft.claims,
            uncertainty=draft.uncertainty,
            recommended_review_steps=draft.recommended_review_steps,
            abstention_reason=draft.abstention_reason,
            citations=citations,
            provider=self.provider.name,
            model=self.provider.model,
            signal_artifact_sha256=hashlib.sha256(signal_bytes).hexdigest(),
            evidence_set_sha256=hashlib.sha256(evidence_bytes).hexdigest(),
        )
        path = (
            signals_path.parent
            / "briefs"
            / f"{brief_key(drug, event)}.json"
        )
        atomic_write(path, canonical_json_bytes(brief.model_dump(mode="json")))
        return BriefingResult(
            status=brief.status,
            brief_path=str(path.relative_to(self.data_dir)),
            citations=len(citations),
        )

    @staticmethod
    def _signal_exists(content: bytes, drug: str, event: str) -> bool:
        target = (drug.upper(), event.upper())
        for line in content.splitlines():
            if line:
                row = json.loads(line)
                if (row["drug"].upper(), row["event"].upper()) == target:
                    return True
        return False

