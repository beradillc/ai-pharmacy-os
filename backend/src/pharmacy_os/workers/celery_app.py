"""Celery application factory.

Celery is an optional dependency; import lazily so the API can boot without it.
Tasks (forecasting, embeddings, sync, regulatory submission) are added from
the sprints that own them.
"""

from __future__ import annotations

from typing import Any

from pharmacy_os.core.config import get_settings


def create_celery_app() -> Any:
    from celery import Celery  # local import: optional dependency

    settings = get_settings()
    app = Celery("pharmacy_os", broker=settings.redis.url, backend=settings.redis.url)
    app.conf.task_default_queue = "pharmacy_os"
    return app
