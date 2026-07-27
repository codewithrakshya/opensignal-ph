from datetime import date

import pytest

from opensignal.adjusted.longitudinal import (
    LongitudinalCohortRecord,
    validate_cohort_contract,
)


def record(person: str, cohort: str) -> LongitudinalCohortRecord:
    return LongitudinalCohortRecord(
        person_id=person,
        cohort=cohort,
        exposure_start=date(2025, 1, 1),
        observation_start=date(2024, 1, 1),
        observation_end=date(2025, 12, 31),
        age=50,
        sex="female",
    )


def test_longitudinal_contract_requires_active_comparator() -> None:
    validate_cohort_contract([record("a", "target"), record("b", "comparator")])
    with pytest.raises(ValueError, match="exactly two"):
        validate_cohort_contract([record("a", "target")])
