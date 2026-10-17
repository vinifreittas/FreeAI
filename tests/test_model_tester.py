import pytest

from freeai.core.config import ModelConfig, ProviderConfig, ResolvedTarget, Settings
from freeai.services.model_tester import check_all_models, ping_model


@pytest.mark.asyncio
async def test_single_model_without_key():
    target = ResolvedTarget(
        target_id="test-chat",
        litellm_model="gemini/test-chat",
        provider_id="gemini",
        api_key_env="GOOGLE_API_KEY",
        types=["chat"],
    )
    result = await ping_model(target, api_key=None)
    assert result.success is False
    assert result.status == "Sem Chave"


@pytest.mark.asyncio
async def test_single_model_chat_success(monkeypatch):
    import litellm

    async def fake_acompletion(**kwargs):
        return {"choices": [{"message": {"content": "pong"}}]}

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    target = ResolvedTarget(
        target_id="test-chat",
        litellm_model="gemini/test-chat",
        provider_id="gemini",
        api_key_env="GOOGLE_API_KEY",
        types=["chat"],
    )
    result = await ping_model(target, api_key="fake-key")
    assert result.success is True
    assert result.status == "OK"
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_single_model_embedding_success(monkeypatch):
    import litellm

    async def fake_aembedding(**kwargs):
        return {"data": [{"embedding": [0.1, 0.2]}]}

    monkeypatch.setattr(litellm, "aembedding", fake_aembedding)

    target = ResolvedTarget(
        target_id="test-embed",
        litellm_model="gemini/test-embed",
        provider_id="gemini",
        api_key_env="GOOGLE_API_KEY",
        types=["embedding"],
    )
    result = await ping_model(target, api_key="fake-key")
    assert result.success is True
    assert result.status == "OK"


@pytest.mark.asyncio
async def test_single_model_ratelimit(monkeypatch):
    import litellm

    async def fake_acompletion(**kwargs):
        raise litellm.RateLimitError("Quota limit reached", model=kwargs["model"], llm_provider="gemini")

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    target = ResolvedTarget(
        target_id="test-chat",
        litellm_model="gemini/test-chat",
        provider_id="gemini",
        api_key_env="GOOGLE_API_KEY",
        types=["chat"],
    )
    result = await ping_model(target, api_key="fake-key")
    assert result.success is True
    assert result.status == "Rate Limit"


@pytest.mark.asyncio
async def test_all_models_runs(monkeypatch):
    import litellm

    async def fake_acompletion(**kwargs):
        return {"choices": [{"message": {"content": "pong"}}]}

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    fake_provider = ProviderConfig(
        id="mock_prov",
        display_name="Mock Provider",
        api_key_env="MOCK_API_KEY",
        models=[
            ModelConfig(id="mock-1", remote_model="mock-1", types=["chat"]),
            ModelConfig(id="mock-2", remote_model="mock-2", types=["chat"]),
        ],
    )
    # Monkeypatch api_key property
    monkeypatch.setattr(ProviderConfig, "api_key", property(lambda self: "mock-key"))

    settings = Settings(providers=[fake_provider])

    results = await check_all_models(settings=settings, max_concurrency=2)
    assert len(results) == 2
    assert all(r.status == "OK" for r in results)
