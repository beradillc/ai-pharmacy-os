"""Every domain event must be resolvable by the relay.

An event the registry doesn't know cannot be rebuilt from its stored payload: the relay
retries it until it dead-letters, and the reaction it should have triggered simply never
happens — silently, and only in the async deployment. Cheap to prevent, so: this test
walks the live class hierarchy rather than a hand-kept list, and fails the moment a new
``DomainEvent`` subclass is added without being registered in ``ALL_EVENTS``.
"""

from __future__ import annotations

import pkgutil
from importlib import import_module

import pharmacy_os.modules
from pharmacy_os.api.v1.outbox_wiring import ALL_EVENTS
from pharmacy_os.core.events import DomainEvent, EventRegistry


def _import_every_module_package() -> None:
    """Load all module packages so ``__subclasses__`` sees every event class."""
    for info in pkgutil.walk_packages(pharmacy_os.modules.__path__, prefix="pharmacy_os.modules."):
        import_module(info.name)


def _all_event_classes() -> set[type[DomainEvent]]:
    """Every production event class. Test-local subclasses (the fakes in
    ``test_outbox_relay``/``test_event_serialization``) are filtered out by origin —
    they are never stored in a real outbox, so requiring them to be registered would
    only teach us to add noise to ``ALL_EVENTS``."""
    _import_every_module_package()
    found: set[type[DomainEvent]] = set()
    pending = list(DomainEvent.__subclasses__())
    while pending:
        cls = pending.pop()
        if cls.__module__.startswith("pharmacy_os."):
            found.add(cls)
        pending.extend(cls.__subclasses__())
    return found


def test_registry_covers_every_domain_event() -> None:
    missing = {cls.__name__ for cls in _all_event_classes()} - {cls.__name__ for cls in ALL_EVENTS}
    assert not missing, (
        f"Domain events missing from ALL_EVENTS (api/v1/outbox_wiring.py): {sorted(missing)}"
    )


def test_registry_resolves_each_registered_event_by_name() -> None:
    registry = EventRegistry()
    registry.register(*ALL_EVENTS)
    for event_type in ALL_EVENTS:
        assert registry.resolve(event_type.__name__) is event_type


def test_all_events_has_no_duplicates() -> None:
    assert len(set(ALL_EVENTS)) == len(ALL_EVENTS)
