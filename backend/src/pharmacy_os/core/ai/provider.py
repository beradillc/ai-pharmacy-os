"""LLM provider port — the seam that keeps the AI vendor swappable (ADR-005).

Only the protocol lives in the kernel. The Anthropic/Claude implementation and
the RAG + guardrail gateway arrive in Sprint 5 (see docs/12_AI_INTEGRATION.md).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class Message:
    role: Role
    content: str


@dataclass(frozen=True, slots=True)
class LLMResult:
    content: str
    model: str
    confidence: float | None = None
    sources: list[dict[str, Any]] = field(default_factory=list)


class LLMProvider(Protocol):
    """Vendor-neutral completion/embedding port."""

    def complete(self, messages: list[Message], *, model: str | None = None) -> LLMResult: ...

    def stream(self, messages: list[Message], *, model: str | None = None) -> Iterator[str]: ...

    def embed(self, text: str) -> list[float]: ...
