import pytest

from opensignal.quality.processor import OpenFDAQualityProcessor
from opensignal.quality.registry import processor_for, supported_sources


def test_registry_exposes_source_processor_contract(tmp_path) -> None:
    assert supported_sources() == ("openfda",)
    assert isinstance(processor_for("openfda", tmp_path), OpenFDAQualityProcessor)


def test_registry_rejects_unknown_source(tmp_path) -> None:
    with pytest.raises(ValueError, match="Unsupported source"):
        processor_for("unknown", tmp_path)
