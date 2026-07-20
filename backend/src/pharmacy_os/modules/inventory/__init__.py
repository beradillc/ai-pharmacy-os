"""Inventory module — batches, event-sourced movements, FEFO (bounded context).

Hexagonal layers: ``domain`` (pure) → ``application`` (use-cases) →
``infrastructure`` (SQLAlchemy) → ``interface`` (HTTP + composition). Compose
via :func:`pharmacy_os.modules.inventory.interface.register`.
"""
