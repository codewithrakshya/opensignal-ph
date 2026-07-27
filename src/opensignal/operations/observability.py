import json
import logging
import time
import uuid
from collections import Counter

from fastapi import Request, Response

logger = logging.getLogger("opensignal.requests")
REQUESTS: Counter[tuple[str, str, int]] = Counter()


async def observe_request(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    started = time.perf_counter()
    response: Response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    REQUESTS[(request.method, request.url.path, response.status_code)] += 1
    response.headers["x-request-id"] = request_id
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": elapsed_ms,
            },
            sort_keys=True,
        )
    )
    return response


def prometheus_metrics() -> str:
    lines = [
        "# HELP opensignal_http_requests_total HTTP requests handled.",
        "# TYPE opensignal_http_requests_total counter",
    ]
    for (method, path, status), count in sorted(REQUESTS.items()):
        lines.append(
            "opensignal_http_requests_total"
            f'{{method="{method}",path="{path}",status="{status}"}} {count}'
        )
    return "\n".join(lines) + "\n"

