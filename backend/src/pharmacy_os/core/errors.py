"""Application error types and their HTTP mapping (RFC 7807 problem+json)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for domain/application errors with an HTTP status."""

    status_code: int = 400
    error_type: str = "about:blank"
    title: str = "Application error"

    def __init__(self, detail: str, *, extra: dict[str, object] | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.extra = extra or {}
        """Additional problem+json members. RFC 7807 §3.2 allows extensions; used
        where a plain string cannot carry the answer — e.g. "which branch?" needs the
        list of branches the caller may pick from."""


class UnauthenticatedError(AppError):
    """No usable credentials — distinct from 403, which means "known but not allowed"."""

    status_code = 401
    error_type = "https://errors.pharmacy-os/unauthenticated"
    title = "Chưa xác thực"


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


class FeatureDisabledError(AppError):
    """Raised when a tenant hasn't opted into a gated feature (e.g. clinical AI)."""

    status_code = 403
    error_type = "https://errors.pharmacy-os/feature-disabled"
    title = "Tính năng chưa được bật"


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    content: dict[str, object] = {
        "type": exc.error_type,
        "title": exc.title,
        "status": exc.status_code,
        "detail": exc.detail,
        "instance": str(request.url.path),
    }
    content.update(exc.extra)
    return JSONResponse(
        status_code=exc.status_code,
        media_type="application/problem+json",
        content=content,
    )


def register_error_handlers(app: FastAPI) -> None:
    """Wire the problem+json handler for every :class:`AppError` subclass."""
    app.add_exception_handler(AppError, _handle_app_error)  # type: ignore[arg-type]
