from datetime import UTC, datetime
from pathlib import Path

from opensignal.benchmark.reference import (
    BenchmarkReferenceEntry,
    BenchmarkReferenceSet,
)


def reviewed_entry() -> BenchmarkReferenceEntry:
    return BenchmarkReferenceEntry(
        reference_id="reviewed-1",
        publication_quarter="2025-Q2",
        source_url="https://www.fda.gov/example",
        source_product_text="Example product",
        source_event_text="Example event",
        normalized_drugs=["example ingredient"],
        normalized_events=["example event"],
        match_method="manual",
        review_status="independently_reviewed",
        reviewed_by="reviewer-id",
        reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_checked_in_seed_is_valid_but_not_benchmark_eligible() -> None:
    reference_set = BenchmarkReferenceSet.from_path(
        Path("reference_sets/fda-potential-signals-2024-2025-seed.json")
    )
    summary = reference_set.validation_summary("2025-Q4")
    assert summary["total_entries"] == 8
    assert summary["eligible_entries"] == 0
    assert summary["exclusion_counts"] == {"not_independently_reviewed": 8}


def test_independently_reviewed_mapping_obeys_temporal_cutoff() -> None:
    entry = reviewed_entry()
    assert entry.eligibility("2025-Q1") == (False, "not_yet_published")
    assert entry.eligibility("2025-Q2") == (True, "eligible")


def test_validation_summary_reports_eligibility() -> None:
    reference_set = BenchmarkReferenceSet(
        reference_set_id="test-v1",
        title="Test",
        source_index="https://www.fda.gov/example",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        entries=[reviewed_entry()],
    )
    assert reference_set.validation_summary("2025-Q2")["eligible_entries"] == 1
