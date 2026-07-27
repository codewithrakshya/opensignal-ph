import json

import pytest
from pydantic import ValidationError

from opensignal.backtesting.reference import load_reference_set


def test_reference_set_requires_explicit_normalized_match(tmp_path) -> None:
    path = tmp_path / "references.json"
    path.write_text(
        json.dumps(
            {
                "reference_set_id": "test-v1",
                "title": "Test",
                "retrieved_at": "2025-01-01T00:00:00Z",
                "entries": [
                    {
                        "reference_id": "r1",
                        "signal_quarter": "2024-Q1",
                        "product_text": "Drug A",
                        "risk_text": "Event X",
                        "match_method": "exact",
                        "source_url": "https://www.fda.gov/example",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_reference_set(path)


def test_versioned_fda_demo_reference_set_loads() -> None:
    reference_set = load_reference_set(
        __import__("pathlib").Path("reference_sets/fda-2025-q2-demo.json")
    )

    assert reference_set.reference_set_id == "fda-2025-q2-demo-v1"
    assert len(reference_set.entries) == 3
    unmatched = sum(
        entry.match_method == "unmatched" for entry in reference_set.entries
    )
    assert unmatched == 1
