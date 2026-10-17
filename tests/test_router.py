import pytest

from freeai.core.config import ResolvedCatalog, ResolvedTarget
from freeai.services import Router


@pytest.fixture
def mock_catalog():
    target_chat = ResolvedTarget(
        target_id="test-chat",
        litellm_model="mock/test-chat",
        provider_id="mock",
        api_key_env="MOCK_KEY",
        types=["chat"],
    )
    target_embed = ResolvedTarget(
        target_id="test-embed",
        litellm_model="mock/test-embed",
        provider_id="mock",
        api_key_env="MOCK_KEY",
        types=["embedding"],
    )
    return ResolvedCatalog(
        routes={
            "chat": [target_chat],
            "embed": [target_embed],
            "test-chat": [target_chat],
        }
    )


def test_router_target_availability(mock_catalog):
    router = Router(catalog=mock_catalog, minute_cooldown_seconds=60)
    target = mock_catalog.get_targets("chat")[0]

    assert router._is_target_available(target) is True

    # Disable provider
    router._disabled_providers.add("mock")
    assert router._is_target_available(target) is False


@pytest.mark.asyncio
async def test_router_no_targets_error(mock_catalog):
    router = Router(catalog=mock_catalog)
    with pytest.raises(RuntimeError, match="Nenhum modelo disponível"):
        await router.acompletion(model="non_existent_route")


def test_router_cooldown_reset(mock_catalog):
    router = Router(catalog=mock_catalog)
    router._disabled_providers.add("mock")
    router._disabled_models.add("test-chat")
    router._cooldowns["mock/test-chat"] = 9999999999.0

    status = router.get_cooldown_status()
    assert "mock" in status["disabled_providers"]
    assert "test-chat" in status["disabled_models"]
    assert "mock/test-chat" in status["cooldowns"]

    router.reset_cooldowns()
    cleared = router.get_cooldown_status()
    assert cleared["disabled_providers"] == []
    assert cleared["disabled_models"] == []
    assert cleared["cooldowns"] == {}


@pytest.mark.asyncio
async def test_router_metadata_attachment(mock_catalog, monkeypatch):
    class FakeResponse:
        pass

    async def fake_acompletion(**kwargs):
        return FakeResponse()

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    router = Router(catalog=mock_catalog)
    res = await router.acompletion(model="chat", messages=[{"role": "user", "content": "hi"}])
    assert getattr(res, "_freeai_provider", None) == "mock"
    assert getattr(res, "_freeai_model", None) == "mock/test-chat"
    assert getattr(res, "_freeai_attempts", None) == 0


def test_router_sync_completion(mock_catalog, monkeypatch):
    class FakeResponse:
        pass

    def fake_completion(**kwargs):
        return FakeResponse()

    import litellm

    monkeypatch.setattr(litellm, "completion", fake_completion)

    router = Router(catalog=mock_catalog)
    res = router.completion(model="chat", messages=[{"role": "user", "content": "hi"}])
    assert getattr(res, "_freeai_provider", None) == "mock"
    assert getattr(res, "_freeai_model", None) == "mock/test-chat"
    assert getattr(res, "_freeai_attempts", None) == 0
