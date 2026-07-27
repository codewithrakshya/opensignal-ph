import json
from importlib import import_module
from typing import Any, Protocol, cast

from opensignal.evidence.models import DraftBrief, DraftClaim, RetrievedEvidence


class BriefProvider(Protocol):
    name: str
    model: str

    def generate(
        self,
        *,
        drug: str,
        event: str,
        evidence: list[RetrievedEvidence],
    ) -> DraftBrief: ...


class TemplateBriefProvider:
    """Offline, deterministic baseline that makes no uncited claims."""

    name = "template"
    model = "deterministic-v1"

    def generate(
        self,
        *,
        drug: str,
        event: str,
        evidence: list[RetrievedEvidence],
    ) -> DraftBrief:
        if not evidence:
            return DraftBrief(
                status="abstained",
                headline="Evidence brief unavailable",
                uncertainty=(
                    "No matching evidence was retrieved. The reporting signal "
                    "does not establish causality."
                ),
                abstention_reason="No relevant evidence was retrieved.",
            )
        claims = [
            DraftClaim(
                text=f"{item.publisher} evidence is available for expert review.",
                citation_ids=[item.document_id],
            )
            for item in evidence
        ]
        return DraftBrief(
            status="generated",
            headline=f"Retrieved evidence context for {drug} and {event}",
            claims=claims,
            uncertainty=(
                "The sources and spontaneous reports support review only; "
                "they do not establish causality or incidence."
            ),
            recommended_review_steps=[
                "Open each cited source and assess clinical relevance.",
                "Review duplicates, confounding, exposure, and temporal sequence.",
            ],
        )


class OpenAIResponsesBriefProvider:
    """Optional Structured Outputs provider; import and credentials are lazy."""

    name = "openai"

    def __init__(self, model: str = "gpt-5.6") -> None:
        self.model = model

    def generate(
        self,
        *,
        drug: str,
        event: str,
        evidence: list[RetrievedEvidence],
    ) -> DraftBrief:
        try:
            openai_module: Any = import_module("openai")
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "Install the optional 'ai' dependency to use the OpenAI provider."
            ) from error
        client = openai_module.OpenAI()
        evidence_json = json.dumps(
            [item.model_dump(mode="json") for item in evidence],
            sort_keys=True,
        )
        response = client.responses.parse(
            model=self.model,
            store=False,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Create a pharmacovigilance evidence brief using only "
                        "the supplied evidence. Every factual claim must cite one "
                        "or more supplied document_id values. Never infer "
                        "causality, incidence, safety, or treatment advice. "
                        "Abstain when evidence is insufficient. Do not reinterpret "
                        "or change the statistical signal decision."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Drug: {drug}\nEvent: {event}\n"
                        f"Evidence JSON: {evidence_json}"
                    ),
                },
            ],
            text_format=DraftBrief,
        )
        if response.output_parsed is None:
            raise RuntimeError("The model returned no structured brief.")
        return cast(DraftBrief, response.output_parsed)
