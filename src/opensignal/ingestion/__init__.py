"""Source adapters and checkpointed ingestion."""

from opensignal.ingestion.manifest import IngestionManifest
from opensignal.ingestion.openfda import OpenFDAClient, OpenFDAQuery
from opensignal.ingestion.runner import IngestionResult, OpenFDAIngestionRunner
from opensignal.ingestion.socrata import SocrataClient, SocrataQuery
from opensignal.ingestion.socrata_manifest import SocrataManifest
from opensignal.ingestion.socrata_runner import SocrataIngestionRunner
from opensignal.ingestion.storage import RawSnapshotStore

__all__ = [
    "IngestionManifest",
    "IngestionResult",
    "OpenFDAClient",
    "OpenFDAIngestionRunner",
    "OpenFDAQuery",
    "RawSnapshotStore",
    "SocrataClient",
    "SocrataIngestionRunner",
    "SocrataManifest",
    "SocrataQuery",
]
