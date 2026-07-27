from collections.abc import Callable
from pathlib import Path

from opensignal.quality.base import SnapshotProcessor
from opensignal.quality.processor import OpenFDAQualityProcessor
from opensignal.quality.wastewater import CDCWastewaterQualityProcessor

ProcessorFactory = Callable[[Path], SnapshotProcessor]

PROCESSORS: dict[str, ProcessorFactory] = {
    "cdc-wastewater": CDCWastewaterQualityProcessor,
    "openfda": OpenFDAQualityProcessor,
}


def supported_sources() -> tuple[str, ...]:
    return tuple(sorted(PROCESSORS))


def processor_for(source: str, data_dir: Path) -> SnapshotProcessor:
    try:
        factory = PROCESSORS[source]
    except KeyError as error:
        raise ValueError(f"Unsupported source: {source}") from error
    return factory(data_dir)
