"""CRM module — customer/patient records (bounded context).

Hexagonal layers: ``domain`` (pure) → ``application`` (use-cases) →
``infrastructure`` (SQLAlchemy) → ``interface`` (HTTP + composition). Compose
via :func:`pharmacy_os.modules.crm.interface.register`.
"""
