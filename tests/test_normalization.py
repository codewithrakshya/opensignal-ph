from opensignal.quality.contracts import OpenFDADrug
from opensignal.quality.normalization import (
    normalize_drug_name,
    normalize_drug_role,
    normalize_patient_age,
    normalize_patient_sex,
    normalize_term,
)


def test_drug_name_uses_standardized_name_before_reported_name() -> None:
    drug = OpenFDADrug.model_validate(
        {
            "medicinalproduct": "Brand Name",
            "openfda": {"generic_name": ["  active   ingredient "]},
        }
    )

    assert normalize_drug_name(drug) == (
        "ACTIVE INGREDIENT",
        "openfda_generic_name",
    )


def test_normalization_collapses_whitespace_and_maps_roles() -> None:
    assert normalize_term(" acute   kidney injury ") == "ACUTE KIDNEY INJURY"
    assert normalize_drug_role("1") == "primary_suspect"
    assert normalize_drug_role("99") == "unknown"


def test_normalize_patient_covariates() -> None:
    assert normalize_patient_sex("2") == "female"
    assert normalize_patient_sex(None) == "unknown"
    assert normalize_patient_age("70", "804") == (70.0, "65+")
    assert normalize_patient_age("18", "802")[1] == "0-1"
    assert normalize_patient_age("invalid", "804") == (None, "unknown")
