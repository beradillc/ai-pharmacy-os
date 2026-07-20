"""Application error types and their HTTP mapping (RFC 7807 problem+json)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for domain/application errors with an HTTP status."""

    status_code: int = 400
    error_type: str = "about:blank"
    title: str = "Application error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    status_code = 404
    error_type = "https://errors.pharmacy-os/not-found"
    title = "Không tìm thấy tài nguyên"


class ValidationError(AppError):
    status_code = 422
    error_type = "https://errors.pharmacy-os/validation"
    title = "Dữ liệu không hợp lệ"


class PermissionDeniedError(AppError):
    status_code = 403
    error_type = "https://errors.pharmacy-os/permission-denied"
    title = "Không đủ quyền"


class ConflictError(AppError):
    status_code = 409
    error_type = "https://errors.pharmacy-os/conflict"
    title = "Xung đột dữ liệu"


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        media_type="application/problem+json",
        content={
            "type": exc.error_type,
            "title": exc.title,
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Wire the problem+json handler for every :class:`AppError` subclass."""
    app.add_exception_handler(AppError, _handle_app_error)  # type: ignore[arg-type]
