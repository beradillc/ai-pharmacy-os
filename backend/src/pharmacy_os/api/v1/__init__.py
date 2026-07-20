"""API v1 router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from pharmacy_os.api.v1.health import router as health_router

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(health_router)

__all__ = ["api_v1"]
