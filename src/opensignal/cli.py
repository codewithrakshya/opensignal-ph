import argparse
import asyncio
import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from opensignal.backtesting.pipeline import BacktestPipeline
from opensignal.core.config import get_settings
from opensignal.detection.pipeline import OpenFDAScoringPipeline
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
    raise AssertionError(f"Unhandled command: {args.command}")
