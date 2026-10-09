from freeai.api.gateway_manager import get_gateway_info, is_gateway_running


def test_gateway_manager_status():
    info = get_gateway_info()
    assert isinstance(info, dict)
    assert "running" in info
    assert "port" in info
    assert "url" in info
    assert is_gateway_running() is False


def test_clear_gateway_cooldowns_no_crash():
    from freeai.api.gateway_manager import clear_gateway_cooldowns

    # Returns False without crashing when gateway is not running
    assert clear_gateway_cooldowns() is False


def test_chat_completions_diagnostic_headers(monkeypatch):
    from fastapi.testclient import TestClient

    from freeai.api.server import create_app
    from freeai.core import get_settings
    from freeai.core.config import ResolvedCatalog, ResolvedTarget
    from freeai.services import Router

    monkeypatch.setattr(get_settings(), "FREEAI_API_KEY", "")

    class FakeResponse:
        def model_dump(self):
            return {"id": "chatcmpl-123", "choices": []}

    target = ResolvedTarget(
        target_id="mock-chat",
        litellm_model="groq/llama-3.3-70b-versatile",
        provider_id="groq",
        api_key_env="GROQ_KEY",
        types=["chat"],
    )
    catalog = ResolvedCatalog(routes={"chat": [target]})
    router = Router(catalog=catalog)

    async def fake_acompletion(**kwargs):
        resp = FakeResponse()
        resp._freeai_provider = "groq"
        resp._freeai_model = "groq/llama-3.3-70b-versatile"
        resp._freeai_attempts = 1
        return resp

    router.acompletion = fake_acompletion

    app = create_app(router_instance=router)
    client = TestClient(app)

    res = client.post("/v1/chat/completions", json={"model": "chat", "messages": []})
    assert res.status_code == 200
    assert res.headers.get("x-freeai-provider") == "groq"
    assert res.headers.get("x-freeai-model") == "groq/llama-3.3-70b-versatile"
    assert res.headers.get("x-freeai-fallback-attempts") == "1"
