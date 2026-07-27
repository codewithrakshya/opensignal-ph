import re

from opensignal.evidence.models import EvidenceDocument, RetrievedEvidence

TOKEN = re.compile(r"[a-z0-9]+")


def tokens(value: str) -> set[str]:
    return set(TOKEN.findall(value.lower()))


def retrieve_evidence(
    documents: list[EvidenceDocument],
    *,
    drug: str,
    event: str,
    limit: int = 5,
) -> list[RetrievedEvidence]:
    """Rank a versioned evidence set with deterministic lexical retrieval."""
    query = tokens(f"{drug} {event}")
    ranked: list[tuple[float, EvidenceDocument]] = []
    for document in documents:
        searchable = tokens(f"{document.title} {document.content}")
        overlap = len(query & searchable)
        if overlap == 0:
            continue
        score = overlap / max(len(query), 1)
        ranked.append((min(score, 1.0), document))
    ranked.sort(key=lambda item: (-item[0], item[1].document_id))
    return [
        RetrievedEvidence(
            document_id=document.document_id,
            title=document.title,
            publisher=document.publisher,
            url=document.url,
            published_date=document.published_date,
            excerpt=document.content[:600],
            relevance_score=score,
        )
        for score, document in ranked[:limit]
    ]

