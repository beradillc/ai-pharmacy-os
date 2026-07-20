from dataclasses import dataclass
from uuid import uuid4

from pharmacy_os.core.events import DomainEvent, InMemoryEventBus


@dataclass(frozen=True, kw_only=True)
class ThingHappened(DomainEvent):
    value: int


async def test_bus_delivers_to_subscriber() -> None:
    bus = InMemoryEventBus()
    seen: list[int] = []

    async def handler(event: DomainEvent) -> None:
        assert isinstance(event, ThingHappened)
        seen.append(event.value)

    bus.subscribe(ThingHappened, handler)
    await bus.publish(ThingHappened(tenant_id=uuid4(), value=42))

    assert seen == [42]


async def test_faulty_handler_is_isolated() -> None:
    bus = InMemoryEventBus()
    delivered: list[int] = []

    async def boom(_event: DomainEvent) -> None:
        raise RuntimeError("handler failure")

    async def ok(event: DomainEvent) -> None:
        assert isinstance(event, ThingHappened)
        delivered.append(event.value)

    bus.subscribe(ThingHappened, boom)
    bus.subscribe(ThingHappened, ok)
    await bus.publish(ThingHappened(tenant_id=uuid4(), value=7))

    assert delivered == [7]  # second handler still ran
