import argparse
import asyncio
import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from opensignal.core.config import get_settings
from opensignal.ingestion.manifest import IngestionManifest
from opensignal.ingestion.openfda import OpenFDAClient
from opensignal.ingestion.runner import OpenFDAIngestionRunner
from opensignal.ingestion.storage import RawSnapshotStore
from opensignal.quality.registry import processor_for, supported_sources


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


def process(source: str, snapshot_id: str) -> int:
    settings = get_settings()
    result = processor_for(source, settings.data_dir).process(snapshot_id)
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "ingest":
        return asyncio.run(ingest(args.manifest))
    if args.command == "process":
        return process(args.source, args.snapshot_id)
    raise AssertionError(f"Unhandled command: {args.command}")
