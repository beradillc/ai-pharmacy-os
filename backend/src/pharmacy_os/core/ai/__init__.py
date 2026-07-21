"""AI gateway port. Concrete providers (Claude) are wired in Sprint 5."""

from pharmacy_os.core.ai.mock import MockLLMProvider
from pharmacy_os.core.ai.provider import LLMProvider, LLMResult, Message

__all__ = ["LLMProvider", "LLMResult", "Message", "MockLLMProvider"]
