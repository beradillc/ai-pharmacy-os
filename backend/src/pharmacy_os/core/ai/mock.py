"""Deterministic in-process ``LLMProvider`` for development and tests.

Makes **no** network call — the Anthropic/Claude adapter is a later concern:

    # BLOCKER: AI__API_KEY thật — the real AnthropicProvider (docs/12) needs a live
    # API key + vendor SDK. Until then this mock stands in so the clinical use-cases
    # (explanation + audit) can run end-to-end without any external dependency.

The mock only *explains*; it never decides safety. In the clinical flow the
safety-critical verdict (which ingredient pairs interact, and how seriously) is
computed deterministically from the ``drug_interactions`` reference table by the
domain engine — the LLM output is advisory and always subject to the pharmacist
review guardrail (docs/12 mục 1, 6).
"""

from __future__ import annotations

from collections.abc import Iterator
from hashlib import sha256

from pharmacy_os.core.ai.provider import LLMResult, Message

_DEFAULT_MODEL = "mock-llm"
_DEFAULT_CONFIDENCE = 0.75
_DEFAULT_EMBED_DIM = 8


class MockLLMProvider:
    """A canned, reproducible :class:`LLMProvider` implementation.

    Output is a deterministic function of the input messages, so tests can assert on
    it. ``confidence`` is fixed at construction time so callers can exercise both sides
    of the review guardrail (a low value forces pharmacist review; a high one does not).
    """

    def __init__(
        self,
        *,
        model: str = _DEFAULT_MODEL,
        confidence: float = _DEFAULT_CONFIDENCE,
        embed_dim: int = _DEFAULT_EMBED_DIM,
    ) -> None:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence phải trong khoảng [0, 1]")
        self._model = model
        self._confidence = confidence
        self._embed_dim = embed_dim

    def complete(self, messages: list[Message], *, model: str | None = None) -> LLMResult:
        prompt = "\n".join(m.content for m in messages)
        content = (
            "[MOCK LLM — không gọi API thật] Diễn giải tự động cho "
            f"{len(prompt)} ký tự ngữ cảnh. Quyết định an toàn do bảng "
            "drug_interactions quyết định (tất định), phần này chỉ để tham khảo."
        )
        return LLMResult(
            content=content,
            model=model or self._model,
            confidence=self._confidence,
            sources=[],
        )

    def stream(self, messages: list[Message], *, model: str | None = None) -> Iterator[str]:
        yield self.complete(messages, model=model).content

    def embed(self, text: str) -> list[float]:
        """Deterministic pseudo-embedding — NOT a real semantic vector (mock only)."""
        digest = sha256(text.encode("utf-8")).digest()
        return [digest[i % len(digest)] / 255.0 for i in range(self._embed_dim)]
