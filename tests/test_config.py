from freeai.core import Settings, build_router_catalog, get_settings
from freeai.core.config import AliasConfig, ModelConfig, ProviderConfig, ResolvedCatalog


def test_settings_load():
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.PORT > 0
    assert len(settings.providers) > 0


def test_build_router_catalog():
    provider = ProviderConfig(
        id="mock_provider",
        display_name="Mock Provider",
        api_key_env="MOCK_KEY",
        models=[
            ModelConfig(id="mock-chat-1", remote_model="chat-1", types=["chat"]),
            ModelConfig(id="mock-embed-1", remote_model="embed-1", types=["embedding"]),
        ],
    )
    # Inject fake api key for mock_provider
    provider.api_key_env = "PATH"  # PATH environment variable always exists

    alias = AliasConfig(alias="chat", models_types_to_chain=["chat"])

    settings = Settings(
        providers=[provider],
        aliases=[alias],
    )

    catalog = build_router_catalog(settings)
    assert isinstance(catalog, ResolvedCatalog)

    chat_targets = catalog.get_targets("chat")
    assert len(chat_targets) == 1
    assert chat_targets[0].litellm_model == "mock_provider/chat-1"


def test_provider_token_removal_inactivates(tmp_path, monkeypatch):
    from freeai.core.storage import save_vault

    test_vault_file = tmp_path / ".test_vault.json"
    monkeypatch.setenv("FREEAI_VAULT_PATH", str(test_vault_file))

    # 1. Save active validated key in vault
    save_vault({"TEST_REM_KEY": "valid-secret-token", "TEST_REM_KEY_VALIDATED": True})
    provider = ProviderConfig(
        id="rem_provider",
        display_name="Removal Provider",
        api_key_env="TEST_REM_KEY",
        models=[ModelConfig(id="rem-model", remote_model="rem-v1", types=["chat"])],
    )
    assert provider.api_key == "valid-secret-token"

    # 2. Remove key from vault (empty string) -> inactive
    save_vault({"TEST_REM_KEY": "", "TEST_REM_KEY_VALIDATED": False})
    assert provider.api_key is None

    # 3. Key present but explicitly not validated -> also inactive
    save_vault({"TEST_REM_KEY": "some-key", "TEST_REM_KEY_VALIDATED": False})
    assert provider.api_key is None

    settings = Settings(providers=[provider])
    catalog = build_router_catalog(settings)
    assert catalog.get_targets("rem-model") == []
