import os

from freeai.config import get_all_provider_keys, get_settings
from freeai.router import build_router


def test_build_router_initialization():
    """Test standard router initialization from models.yaml configuration."""
    router = build_router()

    assert router is not None
    assert len(router.model_list) > 0


def test_router_model_aliases():
    """Test that configured aliases are correctly mapped in litellm Router model_list."""
    router = build_router()

    model_names = {item["model_name"] for item in router.model_list}
    expected_aliases = {"chat", "fast", "large", "coder", "reasoning", "embed", "tts", "stt"}

    for alias in expected_aliases:
        assert alias in model_names, f"Alias '{alias}' expected in model_list"


def test_router_settings_integration(monkeypatch):
    """Test API key environment injection during router creation."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")

    # Clear cached settings to load environment override
    get_settings.cache_clear()

    router = build_router()
    assert router is not None

    # Reset cached settings back
    get_settings.cache_clear()


def test_generic_provider_key_injection(monkeypatch):
    """Test that arbitrary provider keys (e.g. MISTRAL_API_KEY) are dynamically injected."""
    monkeypatch.setenv("MISTRAL_API_KEY", "test_mistral_key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test_deepseek_key")

    keys = get_all_provider_keys()
    assert keys.get("MISTRAL_API_KEY") == "test_mistral_key"
    assert keys.get("DEEPSEEK_API_KEY") == "test_deepseek_key"

    build_router()
    assert os.environ.get("MISTRAL_API_KEY") == "test_mistral_key"
