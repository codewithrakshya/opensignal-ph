from datetime import date

from opensignal.detection.contingency import (
    ContingencyBuilder,
    DrugEventObservation,
)


def test_builder_uses_unique_reports_for_two_by_two_table() -> None:
    observations = [
        DrugEventObservation("r1", date(2025, 1, 1), "DRUG A", "EVENT X"),
        DrugEventObservation("r1", date(2025, 1, 1), "DRUG A", "EVENT X"),
        DrugEventObservation("r2", date(2025, 1, 2), "DRUG A", "EVENT Y"),
        DrugEventObservation("r3", date(2025, 1, 3), "DRUG B", "EVENT X"),
        DrugEventObservation("r4", date(2025, 1, 4), "DRUG B", "EVENT Y"),
    ]
    builder = ContingencyBuilder(observations)

    table = builder.build("DRUG A", "EVENT X")

    assert (table.a, table.b, table.c, table.d) == (1, 1, 1, 1)
    assert builder.analysis_date == date(2025, 1, 4)
    assert builder.candidate_pairs() == [
        ("DRUG A", "EVENT X"),
        ("DRUG A", "EVENT Y"),
        ("DRUG B", "EVENT X"),
        ("DRUG B", "EVENT Y"),
    ]
