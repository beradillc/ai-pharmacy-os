"""Structured logging configuration (structlog)."""

from __future__ import annotations

import logging

import structlog


def configure_logging(*, debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(format="%(message)s", level=level)
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        processors=[
            # 🔴 PHẢI đứng đầu: nó là thứ đưa `request_id` (bind bởi RequestIdMiddleware)
            # vào MỌI dòng log của request đó. Thiếu processor này thì middleware vẫn chạy,
            # header vẫn trả về, và mã vẫn **không xuất hiện trong log** — cổng xanh, tính
            # năng chết. Đúng họ "chuỗi nối hai thế giới" của kỷ luật #22.
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        cache_logger_on_first_use=True,
    )
