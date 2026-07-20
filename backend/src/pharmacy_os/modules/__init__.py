"""Business modules (bounded contexts).

Empty in Sprint 2 by design — the kernel ships first. Modules land from
Sprint 3 onward: catalog, inventory, sales, prescription, clinical, crm,
procurement, compliance, analytics, iam. Each registers its router and event
handlers via a ``register(container)`` hook.
"""
