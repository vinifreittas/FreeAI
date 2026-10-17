import pytest

from freeai.services.key_validator import validate_provider_key


@pytest.mark.asyncio
async def test_key_validator_empty():
    ok, msg = await validate_provider_key("gemini", "")
    assert ok is False
    assert "não informada" in msg


@pytest.mark.asyncio
async def test_key_validator_unknown_provider():
    ok, msg = await validate_provider_key("unknown_provider", "some-token")
    assert ok is False
    assert "não possui modelos" in msg


@pytest.mark.asyncio
async def test_key_validator_success(monkeypatch):
    import litellm

    async def fake_acompletion(**kwargs):
        return {"choices": [{"message": {"content": "pong"}}]}

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    ok, msg = await validate_provider_key("gemini", "valid-key")
    assert ok is True
    assert "sucesso" in msg


@pytest.mark.asyncio
async def test_key_validator_fallback_to_second_model(monkeypatch):
    import litellm

    attempts = []

    async def fake_acompletion(**kwargs):
        attempts.append(kwargs["model"])
        if len(attempts) == 1:
            raise litellm.NotFoundError("model deprecated", model=kwargs["model"], llm_provider="gemini")
        return {"choices": [{"message": {"content": "pong"}}]}

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    ok, msg = await validate_provider_key("gemini", "valid-key")
    assert ok is True
    assert len(attempts) >= 2
    assert "sucesso" in msg


@pytest.mark.asyncio
async def test_key_validator_auth_error_stops_immediately(monkeypatch):
    import litellm

    calls = 0

    async def fake_acompletion(**kwargs):
        nonlocal calls
        calls += 1
        raise litellm.AuthenticationError("invalid key", model=kwargs["model"], llm_provider="gemini")

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    ok, msg = await validate_provider_key("gemini", "invalid-key")
    assert ok is False
    assert calls == 1
    assert "não autorizada" in msg
