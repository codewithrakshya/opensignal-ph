"""Data contracts, validation rules, and quality reporting."""

from opensignal.quality.contracts import (
    CuratedDrugEvent,
    OpenFDAReport,
    QualityReport,
    RejectedRecord,
    ValidatedReport,
)
from opensignal.quality.processor import OpenFDAQualityProcessor, ProcessingResult
from opensignal.quality.registry import processor_for, supported_sources

__all__ = [
    "CuratedDrugEvent",
    "OpenFDAQualityProcessor",
    "OpenFDAReport",
    "ProcessingResult",
    "QualityReport",
    "RejectedRecord",
    "ValidatedReport",
    "processor_for",
    "supported_sources",
]
