from fastapi import FastAPI

from opensignal import __version__
from opensignal.api.signals import router as signals_router
from opensignal.api.temporal import router as temporal_router
from opensignal.core.config import get_settings
from opensignal.core.models import HealthResponse

settings = get_settings()

app = FastAPI(
    title="OpenSignal PH",
    version=__version__,
    description=(
        "A research platform for reproducible adverse-event signal detection. "
        "Outputs are potential reporting signals and do not establish causality."
    ),
)
app.include_router(signals_router)
app.include_router(temporal_router)


@app.get("/health", response_model=HealthResponse, tags=["operations"])
def health() -> HealthResponse:
    """Return process health and build metadata."""
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=__version__,
        environment=settings.environment,
    )
