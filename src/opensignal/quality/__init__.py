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
from opensignal.quality.wastewater import CDCWastewaterQualityProcessor
from opensignal.quality.wastewater_contracts import CuratedWastewaterObservation

__all__ = [
    "CuratedDrugEvent",
    "CuratedWastewaterObservation",
    "CDCWastewaterQualityProcessor",
    "OpenFDAQualityProcessor",
    "OpenFDAReport",
    "ProcessingResult",
    "QualityReport",
    "RejectedRecord",
    "ValidatedReport",
    "processor_for",
    "supported_sources",
]
