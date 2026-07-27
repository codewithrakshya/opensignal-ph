from datetime import date
from typing import Protocol

from opensignal.core.models import SignalScore


class SignalDetector(Protocol):
    """Contract implemented by each signal-detection method."""

    name: str

    def score(
        self,
        *,
        drug: str,
        event: str,
        analysis_date: date,
        inputs: object,
    ) -> SignalScore:
        """Calculate and explain one drug-event score."""
        ...
