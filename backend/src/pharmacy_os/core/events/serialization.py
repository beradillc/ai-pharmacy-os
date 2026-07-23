"""Serialize domain events to/from JSON-safe dicts, for the transactional outbox.

An outbox row stores an event as ``event_type`` + a JSON ``payload`` so it can be
re-published after a crash. The codec is **generic** — it walks a frozen-dataclass
event with :func:`dataclasses.fields` and its resolved type hints, so a new event
type needs no bespoke encoder. It deliberately imports **no business module**
(kernel independence): :func:`deserialize_event` is handed the target type, and the
composition root owns the :class:`EventRegistry` that maps a stored ``event_type``
name back to its class.

Round-trip identity (``deserialize_event(t, serialize_event(e)["payload"]) == e``)
is proven for every event type in ``tests/unit/test_event_serialization.py`` — that
suite is the contract this module must keep.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints
from uuid import UUID

from pharmacy_os.core.events.base import DomainEvent


def serialize_event(event: DomainEvent) -> dict[str, Any]:
    """Return ``{"event_type": <class name>, "payload": <JSON-safe dict>}``."""
    return {"event_type": event.name, "payload": _encode(event)}


def deserialize_event(event_type: type[DomainEvent], payload: dict[str, Any]) -> DomainEvent:
    """Rebuild an event of *event_type* from a payload produced by :func:`serialize_event`."""
    value = _decode_dataclass(event_type, payload)
    assert isinstance(value, DomainEvent)  # event_type is a DomainEvent subclass by contract
    return value


def _encode(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _encode(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)  # str, not float — never lose precision on money/quantities
    if isinstance(value, datetime):  # must precede date: datetime is a date subclass
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple | list):
        return [_encode(item) for item in value]
    return value  # str, int, bool, None pass through


def _decode(type_hint: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = get_origin(type_hint)
    if origin is Union or origin is UnionType:  # X | None / Optional[X]
        (non_none,) = [arg for arg in get_args(type_hint) if arg is not type(None)]
        return _decode(non_none, value)
    if origin is tuple:
        (elem_type, _ellipsis) = get_args(type_hint)  # tuple[Elem, ...]
        return tuple(_decode(elem_type, item) for item in value)
    if type_hint is UUID:
        return UUID(value)
    if type_hint is Decimal:
        return Decimal(value)
    if type_hint is datetime:
        return datetime.fromisoformat(value)
    if type_hint is date:
        return date.fromisoformat(value)
    if is_dataclass(type_hint):
        return _decode_dataclass(type_hint, value)
    return value  # str, int, bool


def _decode_dataclass(dataclass_type: Any, data: dict[str, Any]) -> Any:
    hints = get_type_hints(dataclass_type)
    kwargs = {
        f.name: _decode(hints[f.name], data[f.name])
        for f in fields(dataclass_type)
        if f.name in data
    }
    return dataclass_type(**kwargs)


class EventRegistry:
    """Maps a stored ``event_type`` name back to its class, for the outbox relay.

    Lives conceptually at the composition root (it must know every module's events);
    the kernel only defines the shape, never the membership, so ``core`` keeps its
    independence from business modules.
    """

    def __init__(self) -> None:
        self._by_name: dict[str, type[DomainEvent]] = {}

    def register(self, *event_types: type[DomainEvent]) -> None:
        for event_type in event_types:
            self._by_name[event_type.__name__] = event_type

    def resolve(self, event_type_name: str) -> type[DomainEvent] | None:
        return self._by_name.get(event_type_name)
