"""A minimal, explicit dependency-injection container.

Deliberately dependency-free (no third-party DI library) to keep wiring
transparent for a skeleton. Supports singletons and lazy factories. Swap for
``dependency-injector`` later if the graph grows — the interface is small.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

T = TypeVar("T")

Factory = Callable[["Container"], Any]


class Container:
    def __init__(self) -> None:
        self._factories: dict[Any, Factory] = {}
        self._singletons: dict[Any, Factory] = {}
        self._instances: dict[Any, Any] = {}

    def register_singleton(self, key: type[T], factory: Callable[[Container], T]) -> None:
        """Register a factory whose result is created once and cached."""
        self._singletons[key] = factory

    def register_factory(self, key: type[T], factory: Callable[[Container], T]) -> None:
        """Register a factory invoked on every :meth:`resolve`."""
        self._factories[key] = factory

    def register_instance(self, key: type[T], instance: T) -> None:
        """Register a pre-built instance."""
        self._instances[key] = instance

    def resolve(self, key: type[T]) -> T:
        if key in self._instances:
            return cast(T, self._instances[key])
        if key in self._singletons:
            instance = self._singletons[key](self)
            self._instances[key] = instance
            return cast(T, instance)
        if key in self._factories:
            return cast(T, self._factories[key](self))
        raise KeyError(f"No provider registered for {key!r}")

    def has(self, key: type) -> bool:
        return key in self._instances or key in self._singletons or key in self._factories
