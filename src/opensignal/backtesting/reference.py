import json
from pathlib import Path

from opensignal.backtesting.models import ReferenceSet


def load_reference_set(path: Path) -> ReferenceSet:
    if not path.exists():
        raise FileNotFoundError(f"Reference set not found: {path}")
    return ReferenceSet.model_validate(json.loads(path.read_text(encoding="utf-8")))
