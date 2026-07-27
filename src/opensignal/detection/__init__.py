"""Statistical and machine-learning signal detectors."""

from opensignal.detection.prr import ProportionalReportingRatio
from opensignal.detection.ror import ContingencyTable, ReportingOddsRatio

__all__ = [
    "ContingencyTable",
    "ProportionalReportingRatio",
    "ReportingOddsRatio",
]
