import argparse
import asyncio
import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from opensignal.backtesting.pipeline import BacktestPipeline
from opensignal.core.config import get_settings
from opensignal.demo import run_portfolio_demo
from opensignal.detection.pipeline import OpenFDAScoringPipeline
from opensignal.evidence.pipeline import EvidenceBriefingPipeline
from opensignal.evidence.providers import (
    OpenAIResponsesBriefProvider,
    TemplateBriefProvider,
)
from opensignal.ingestion.manifest import IngestionManifest
from opensignal.ingestion.openfda import OpenFDAClient
from opensignal.ingestion.runner import OpenFDAIngestionRunner
from opensignal.ingestion.socrata import SocrataClient
from opensignal.ingestion.socrata_manifest import SocrataManifest
from opensignal.ingestion.socrata_runner import SocrataIngestionRunner
from opensignal.ingestion.storage import RawSnapshotStore
from opensignal.quality.registry import processor_for, supported_sources
from opensignal.temporal.pipeline import OpenFDATemporalPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opensignal")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest", help="Run a bounded openFDA ingestion")
    ingest.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to a versioned ingestion manifest",
    )
    socrata = commands.add_parser(
        "ingest-socrata",
        help="Run a bounded Socrata ingestion",
    )
    socrata.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to a versioned Socrata ingestion manifest",
    )
    process = commands.add_parser(
        "process",
        help="Validate and curate an ingested source snapshot",
    )
    process.add_argument(
        "--source",
        choices=supported_sources(),
        default="openfda",
    )
    process.add_argument("--snapshot-id", required=True)
    score = commands.add_parser(
        "score",
        help="Calculate openFDA statistical signal scores",
    )
    score.add_argument(
        "--source",
        choices=["openfda"],
        default="openfda",
    )
    score.add_argument("--snapshot-id", required=True)
    temporal = commands.add_parser(
        "temporal",
        help="Build quarterly features and temporal ML signal scores",
    )
    temporal.add_argument("--source", choices=["openfda"], default="openfda")
    temporal.add_argument("--snapshot-id", required=True)
    backtest = commands.add_parser(
        "backtest",
        help="Run leakage-resistant walk-forward detector evaluation",
    )
    backtest.add_argument("--source", choices=["openfda"], default="openfda")
    backtest.add_argument("--snapshot-id", required=True)
    backtest.add_argument("--reference-set", type=Path, required=True)
    backtest.add_argument("--k", type=int, default=10)
    brief = commands.add_parser(
        "brief",
        help="Generate a cited, fail-closed evidence brief",
    )
    brief.add_argument("--source", choices=["openfda"], default="openfda")
    brief.add_argument("--snapshot-id", required=True)
    brief.add_argument("--drug", required=True)
    brief.add_argument("--event", required=True)
    brief.add_argument("--evidence-set", type=Path, required=True)
    brief.add_argument(
        "--provider",
        choices=["template", "openai"],
        default="template",
    )
    demo = commands.add_parser(
        "demo",
        help="Run the synthetic end-to-end portfolio demonstration",
    )
    demo.add_argument(
        "--evidence-set",
        type=Path,
        default=Path("evidence_sets/fda-demo-v1.json"),
    )
    return parser


async def ingest(manifest_path: Path) -> int:
    settings = get_settings()
    manifest = IngestionManifest.from_path(manifest_path)
    client = OpenFDAClient(
        settings.openfda_base_url,
        api_key=settings.openfda_api_key,
        max_attempts=settings.openfda_max_attempts,
        backoff_seconds=settings.openfda_backoff_seconds,
    )
    runner = OpenFDAIngestionRunner(
        client=client,
        store=RawSnapshotStore(settings.data_dir, manifest.snapshot_id),
    )
    result = await runner.run(manifest)
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


async def ingest_socrata(manifest_path: Path) -> int:
    settings = get_settings()
    manifest = SocrataManifest.from_path(manifest_path)
    client = SocrataClient(
        manifest.domain,
        manifest.dataset_id,
        app_token=settings.socrata_app_token,
        max_attempts=settings.socrata_max_attempts,
        backoff_seconds=settings.socrata_backoff_seconds,
    )
    runner = SocrataIngestionRunner(
        client=client,
        store=RawSnapshotStore(
            settings.data_dir,
            manifest.snapshot_id,
            source=manifest.source,
        ),
    )
    result = await runner.run(manifest)
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


def process(source: str, snapshot_id: str) -> int:
    settings = get_settings()
    result = processor_for(source, settings.data_dir).process(snapshot_id)
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


def score(source: str, snapshot_id: str) -> int:
    settings = get_settings()
    if source != "openfda":
        raise ValueError(f"Unsupported scoring source: {source}")
    result = OpenFDAScoringPipeline(settings.data_dir).run(snapshot_id)
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


def temporal(source: str, snapshot_id: str) -> int:
    settings = get_settings()
    if source != "openfda":
        raise ValueError(f"Unsupported temporal source: {source}")
    result = OpenFDATemporalPipeline(settings.data_dir).run(snapshot_id)
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


def backtest(
    source: str,
    snapshot_id: str,
    reference_set: Path,
    k: int,
) -> int:
    settings = get_settings()
    if source != "openfda":
        raise ValueError(f"Unsupported backtest source: {source}")
    result = BacktestPipeline(settings.data_dir, k=k).run(
        snapshot_id, reference_set
    )
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


def brief(
    source: str,
    snapshot_id: str,
    drug: str,
    event: str,
    evidence_set: Path,
    provider_name: str,
) -> int:
    settings = get_settings()
    if source != "openfda":
        raise ValueError(f"Unsupported briefing source: {source}")
    provider = (
        OpenAIResponsesBriefProvider(settings.brief_model)
        if provider_name == "openai"
        else TemplateBriefProvider()
    )
    result = EvidenceBriefingPipeline(settings.data_dir, provider).run(
        snapshot_id,
        drug=drug,
        event=event,
        evidence_set=evidence_set,
    )
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "ingest":
        return asyncio.run(ingest(args.manifest))
    if args.command == "ingest-socrata":
        return asyncio.run(ingest_socrata(args.manifest))
    if args.command == "process":
        return process(args.source, args.snapshot_id)
    if args.command == "score":
        return score(args.source, args.snapshot_id)
    if args.command == "temporal":
        return temporal(args.source, args.snapshot_id)
    if args.command == "backtest":
        return backtest(
            args.source, args.snapshot_id, args.reference_set, args.k
        )
    if args.command == "brief":
        return brief(
            args.source,
            args.snapshot_id,
            args.drug,
            args.event,
            args.evidence_set,
            args.provider,
        )
    if args.command == "demo":
        result = run_portfolio_demo(
            get_settings().data_dir,
            args.evidence_set,
        )
        print(json.dumps(asdict(result), sort_keys=True))
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
