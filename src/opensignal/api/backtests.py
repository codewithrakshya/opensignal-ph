import json

from fastapi import APIRouter, HTTPException

from opensignal.backtesting.models import BacktestSummary
from opensignal.core.config import get_settings
from opensignal.ingestion.manifest import SAFE_ID

router = APIRouter(prefix="/backtests", tags=["evaluation"])


@router.get(
    "/{source}/{snapshot_id}/{reference_set_id}",
    response_model=BacktestSummary,
)
def get_backtest_summary(
    source: str,
    snapshot_id: str,
    reference_set_id: str,
) -> BacktestSummary:
    values = (source, snapshot_id, reference_set_id)
    if not all(SAFE_ID.fullmatch(value) for value in values):
        raise HTTPException(status_code=400, detail="Invalid artifact identifier")
    path = (
        get_settings().data_dir
        / "analytics"
        / source
        / snapshot_id
        / "backtests"
        / reference_set_id
        / "summary.json"
    )
    if not path.exists():
        raise HTTPException(status_code=404, detail="Backtest artifact not found")
    return BacktestSummary.model_validate(json.loads(path.read_text(encoding="utf-8")))
