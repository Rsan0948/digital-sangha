# Loopback-only auth model: admin endpoints rely on the backend binding to
# 127.0.0.1 / localhost. They are not exposed off-host and intentionally have
# no further auth.
import math
import threading
import time
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from backend.database import get_session
from backend.services.portability import apply_import, build_export
from backend.services.vector_store import (
    cleanup_orphaned_vectors,
    vector_store_stats,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Stdlib token-bucket rate limiter. Process-restart clears the budget; that is
# acceptable for a loopback-only desktop backend where the only "client" is
# the local frontend. Defaults: cleanup/import 10/min, stats/export 60/min.
_RATE_LIMITS: dict[str, tuple[int, float]] = {
    "vectors_cleanup": (10, 10 / 60),
    "vectors_stats": (60, 60 / 60),
    "export": (60, 60 / 60),
    "import": (10, 10 / 60),
}

_buckets: dict[str, list[float]] = {}
_buckets_lock = threading.Lock()


def _check_rate(endpoint: str) -> None:
    """Token-bucket: refill at ``refill_per_sec`` up to ``capacity``; consume 1."""
    capacity, refill_per_sec = _RATE_LIMITS[endpoint]
    now = time.monotonic()
    with _buckets_lock:
        state = _buckets.get(endpoint)
        if state is None:
            state = [float(capacity), now]
            _buckets[endpoint] = state
        tokens, last = state
        elapsed = max(0.0, now - last)
        tokens = min(float(capacity), tokens + elapsed * refill_per_sec)
        if tokens < 1.0:
            # Round up so a 0.4-token deficit reports "1 second" not "0".
            retry_in = max(1, math.ceil((1.0 - tokens) / refill_per_sec))
            state[0] = tokens
            state[1] = now
            raise HTTPException(
                status_code=429,
                detail=f"rate limit exceeded; try again in {retry_in} seconds",
            )
        state[0] = tokens - 1.0
        state[1] = now


@router.post("/vectors/cleanup")
def cleanup_vectors() -> dict:
    _check_rate("vectors_cleanup")
    return cleanup_orphaned_vectors()


@router.get("/vectors/stats")
def vectors_stats() -> dict:
    _check_rate("vectors_stats")
    return vector_store_stats()


# Loopback-only: same model as the /vectors/* endpoints above.
@router.get("/export")
def export_data(session: Session = Depends(get_session)) -> StreamingResponse:
    _check_rate("export")
    zip_bytes = build_export(session)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"yoga-companion-export-{timestamp}.zip"
    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Loopback-only: same model as the /vectors/* endpoints above.
@router.post("/import")
async def import_data(bundle: UploadFile, session: Session = Depends(get_session)) -> dict:
    _check_rate("import")
    zip_bytes = await bundle.read()
    try:
        return apply_import(zip_bytes, session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
