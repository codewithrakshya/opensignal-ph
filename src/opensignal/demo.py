import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from opensignal.detection.pipeline import OpenFDAScoringPipeline
from opensignal.evidence.pipeline import EvidenceBriefingPipeline
from opensignal.evidence.providers import TemplateBriefProvider
from opensignal.ingestion.storage import atomic_write
from opensignal.temporal.pipeline import OpenFDATemporalPipeline


@dataclass(frozen=True)
class DemoResult:
    snapshot_id: str
    curated_rows: int
    statistical_scores: int
    temporal_scores: int
    brief_status: str
    output_directory: str


def run_portfolio_demo(
    data_dir: Path,
    evidence_set: Path,
    snapshot_id: str = "portfolio-demo",
) -> DemoResult:
    """Run a small, synthetic, non-clinical end-to-end demonstration."""
    rows: list[dict[str, object]] = []
    report = 0
    for quarter, month in enumerate((1, 4, 7, 10), start=1):
        for drug, event, count in (
            ("DRUG A", "EVENT X", 2 if quarter < 4 else 20),
            ("DRUG A", "EVENT Y", 3),
            ("DRUG B", "EVENT X", 3),
            ("DRUG B", "EVENT Y", 12),
        ):
            for _ in range(count):
                report += 1
                rows.append(
                    {
                        "report_id": f"demo-{report:04d}",
                        "received_date": date(2024, month, 10).isoformat(),
                        "drug_name": drug,
                        "reaction": event,
                        "serious": event == "EVENT X" and report % 2 == 0,
                    }
                )
    curated = (
        data_dir
        / "curated"
        / "openfda"
        / snapshot_id
        / "drug_event_pairs.jsonl"
    )
    content = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode()
    atomic_write(curated, content)
    statistical = OpenFDAScoringPipeline(data_dir).run(snapshot_id)
    temporal = OpenFDATemporalPipeline(
        data_dir, contamination=0.125, minimum_history=3
    ).run(snapshot_id)
    brief = EvidenceBriefingPipeline(
        data_dir, TemplateBriefProvider()
    ).run(
        snapshot_id,
        drug="DRUG A",
        event="EVENT X",
        evidence_set=evidence_set,
    )
    result = DemoResult(
        snapshot_id=snapshot_id,
        curated_rows=len(rows),
        statistical_scores=statistical.scores_written,
        temporal_scores=temporal.signal_rows,
        brief_status=brief.status,
        output_directory=str(
            Path("analytics") / "openfda" / snapshot_id
        ),
    )
    atomic_write(
        data_dir / result.output_directory / "demo-result.json",
        (json.dumps(asdict(result), sort_keys=True) + "\n").encode(),
    )
    return result

