"""In-process domain event bus (pub/sub).

The :class:`EventBus` interface is broker-agnostic: swapping the in-process
implementation for RabbitMQ/Kafka later requires no domain changes.
"""

from pharmacy_os.core.events.base import DomainEvent
from pharmacy_os.core.events.bus import EventBus, InMemoryEventBus
from pharmacy_os.core.events.serialization import (
    EventRegistry,
    deserialize_event,
    serialize_event,
)

__all__ = [
    "DomainEvent",
    "EventBus",
    "InMemoryEventBus",
    "EventRegistry",
    "deserialize_event",
    "serialize_event",
]
