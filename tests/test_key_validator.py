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
