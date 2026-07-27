import re

from opensignal.quality.contracts import OpenFDADrug

WHITESPACE = re.compile(r"\s+")
ROLE_NAMES = {
    "1": "primary_suspect",
    "2": "secondary_suspect",
    "3": "concomitant",
    "4": "interacting",
}


def normalize_term(value: str) -> str:
    return WHITESPACE.sub(" ", value.strip()).upper()


def normalize_drug_name(drug: OpenFDADrug) -> tuple[str | None, str]:
    candidates = (
        (drug.openfda.generic_name, "openfda_generic_name"),
        (drug.openfda.substance_name, "openfda_substance_name"),
        (drug.openfda.brand_name, "openfda_brand_name"),
    )
    for values, source in candidates:
        normalized = sorted(
            {normalize_term(value) for value in values if value.strip()}
        )
        if normalized:
            return normalized[0], source

    if drug.medicinalproduct and drug.medicinalproduct.strip():
        return normalize_term(drug.medicinalproduct), "reported_medicinal_product"
    return None, "missing"


def normalize_drug_role(value: str | None) -> str:
    if value is None:
        return "unknown"
    return ROLE_NAMES.get(value, "unknown")
