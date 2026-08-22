from freeai.config import get_settings


def test_settings_load() -> None:
    settings = get_settings()
    assert settings is not None
    assert len(settings.providers) > 0
    assert len(settings.aliases) > 0


def test_alias_resolution() -> None:
    settings = get_settings()
    model, provider, alias = settings.resolve_alias("chat")
    assert alias is not None
    assert alias.alias == "chat"
    assert model is not None
    assert provider is not None


def test_fallbacks_generation() -> None:
    settings = get_settings()
    fallbacks = settings.get_fallbacks_for("chat")
    assert isinstance(fallbacks, list)
    assert len(fallbacks) > 0
