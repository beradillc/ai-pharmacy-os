"""Prescription domain exceptions (pure — no framework)."""

from __future__ import annotations


class PrescriptionError(Exception):
    """Base for prescription domain rule violations."""


class EmptyPrescriptionError(PrescriptionError):
    """Raised when validating a prescription that has no items."""


class InvalidPrescriptionStateError(PrescriptionError):
    """Raised on an operation not allowed in the prescription's current status."""


class InvalidPrescriptionImageError(PrescriptionError):
    """Ảnh đơn thuốc không hợp lệ — sai định dạng, rỗng, hoặc quá lớn.

    Giới hạn kích thước ở đây là **cổng**, không phải sự tiện lợi. Máy khách đã thu nhỏ
    ảnh trước khi gửi, nhưng "máy khách đã làm" chưa bao giờ là một bảo đảm: một ảnh
    điện thoại thô 5 MB qua base64 rồi mã hoá rồi base64 lần nữa thành ~9 MB **một dòng**.
    Vài chục dòng như thế mỗi ngày là `pg_dump` chậm tới mức người ta thôi chạy nó — và
    mất backup tệ hơn nhiều so với mất một tấm ảnh.
    """
