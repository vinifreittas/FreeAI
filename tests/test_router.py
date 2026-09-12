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
