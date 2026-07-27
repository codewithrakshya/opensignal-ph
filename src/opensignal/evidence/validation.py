import re

from opensignal.evidence.models import DraftBrief, RetrievedEvidence

UNSAFE_PATTERNS = (
    re.compile(r"\bcauses?\b", re.IGNORECASE),
    re.compile(r"\bproves?\b", re.IGNORECASE),
    re.compile(r"\bstop taking\b", re.IGNORECASE),
    re.compile(r"\b(start|change) (a |your )?(dose|treatment)\b", re.IGNORECASE),
    re.compile(r"\b(is|are) (safe|unsafe)\b", re.IGNORECASE),
)


def validation_errors(
    draft: DraftBrief,
    evidence: list[RetrievedEvidence],
) -> list[str]:
    """Return grounding and safety violations; an empty list means valid."""
    if draft.status == "abstained":
        if draft.claims:
            return ["abstained briefs cannot contain claims"]
        return []
    if not evidence:
        return ["generated brief has no retrieved evidence"]
    if not draft.claims:
        return ["generated brief has no claims"]
    evidence_ids = {item.document_id for item in evidence}
    errors: list[str] = []
    for index, claim in enumerate(draft.claims):
        unknown = set(claim.citation_ids) - evidence_ids
        if unknown:
            errors.append(
                f"claim {index} cites unavailable evidence: {sorted(unknown)}"
            )
    all_text = " ".join(
        [draft.headline, draft.uncertainty, *(item.text for item in draft.claims)]
    )
    if any(pattern.search(all_text) for pattern in UNSAFE_PATTERNS):
        errors.append("brief contains causal, safety, or treatment language")
    return errors


def abstention(reason: str) -> DraftBrief:
    return DraftBrief(
        status="abstained",
        headline="Evidence brief unavailable",
        uncertainty=(
            "The reporting signal remains a hypothesis for expert review and "
            "does not establish causality."
        ),
        abstention_reason=reason,
    )

