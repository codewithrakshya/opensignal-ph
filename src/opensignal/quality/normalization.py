import re

from opensignal.quality.contracts import OpenFDADrug

WHITESPACE = re.compile(r"\s+")
ROLE_NAMES = {
    "1": "primary_suspect",
    "2": "secondary_suspect",
    "3": "concomitant",
    "4": "interacting",
}
SEX_NAMES = {"0": "unknown", "1": "male", "2": "female"}
AGE_UNIT_TO_YEARS = {
    "800": 1 / 8760,
    "801": 1 / 365,
    "802": 1 / 52.1429,
    "803": 1 / 12,
    "804": 1,
    "805": 10,
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


def normalize_patient_sex(value: str | None) -> str:
    return SEX_NAMES.get(value or "0", "unknown")


def normalize_patient_age(
    value: str | None,
    unit: str | None,
) -> tuple[float | None, str]:
    if value is None or unit not in AGE_UNIT_TO_YEARS:
        return None, "unknown"
    try:
        years = float(value) * AGE_UNIT_TO_YEARS[unit]
    except ValueError:
        return None, "unknown"
    if not 0 <= years <= 130:
        return None, "unknown"
    if years < 2:
        group = "0-1"
    elif years < 18:
        group = "2-17"
    elif years < 45:
        group = "18-44"
    elif years < 65:
        group = "45-64"
    else:
        group = "65+"
    return round(years, 3), group
