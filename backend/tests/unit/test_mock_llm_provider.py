import pytest

from pharmacy_os.core.ai import Message, MockLLMProvider


def _messages() -> list[Message]:
    return [
        Message(role="system", content="bạn là trợ lý dược"),
        Message(role="user", content="aspirin × warfarin"),
    ]


def test_complete_is_deterministic() -> None:
    provider = MockLLMProvider()
    first = provider.complete(_messages())
    second = provider.complete(_messages())
    assert first == second
    assert first.model == "mock-llm"
    assert first.confidence == 0.75
    assert "MOCK" in first.content


def test_complete_respects_model_override() -> None:
    provider = MockLLMProvider()
    result = provider.complete(_messages(), model="claude-opus-4-8")
    assert result.model == "claude-opus-4-8"


def test_confidence_is_configurable() -> None:
    assert MockLLMProvider(confidence=0.2).complete(_messages()).confidence == 0.2


def test_confidence_out_of_range_rejected() -> None:
    with pytest.raises(ValueError):
        MockLLMProvider(confidence=1.5)


def test_stream_yields_the_completion() -> None:
    provider = MockLLMProvider()
    chunks = list(provider.stream(_messages()))
    assert "".join(chunks) == provider.complete(_messages()).content


def test_embed_is_deterministic_and_sized() -> None:
    provider = MockLLMProvider(embed_dim=8)
    vec = provider.embed("paracetamol")
    assert len(vec) == 8
    assert vec == provider.embed("paracetamol")
    assert all(0.0 <= x <= 1.0 for x in vec)
