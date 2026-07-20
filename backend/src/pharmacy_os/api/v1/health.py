"""Health & readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from pharmacy_os import __version__

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    version: str
    service: str = "ai-pharmacy-os"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — the process is up and serving."""
    return HealthResponse(status="ok", version=__version__)
