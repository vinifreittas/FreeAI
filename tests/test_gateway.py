from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from freeai.config import get_settings
from freeai.gateway.server import create_app


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("FREEAI_API_KEY", "test-token")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_router():
    router = MagicMock()
    router.model_list = [
        {"model_name": "chat"},
        {"model_name": "fast"},
        {"model_name": "coder"},
    ]
    router.acompletion = AsyncMock(
        return_value={"id": "chat-123", "choices": [{"message": {"content": "Olá, mundo!"}}]}
    )
    router.aembedding = AsyncMock(return_value={"object": "list", "data": [{"embedding": [0.1, 0.2, 0.3]}]})
    return router


@pytest.fixture
def client(mock_router):
    app = create_app(router_instance=mock_router)
    return TestClient(app)


def test_auth_missing_header(client):
    """Test response when Authorization header is missing."""
    response = client.get("/v1/models")
    assert response.status_code == 401
    assert "Token de autorização ausente" in response.json()["detail"]


def test_auth_invalid_token(client):
    """Test response when Authorization token is invalid."""
    response = client.get("/v1/models", headers={"Authorization": "Bearer invalid-key"})
    assert response.status_code == 401
    assert "API Key inválida" in response.json()["detail"]


def test_list_models_success(client):
    """Test /v1/models endpoint with valid authorization."""
    settings = get_settings()
    response = client.get(
        "/v1/models",
        headers={"Authorization": f"Bearer {settings.FREEAI_API_KEY}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    model_ids = [m["id"] for m in payload["data"]]
    assert "chat" in model_ids
    assert "fast" in model_ids
    assert "coder" in model_ids


def test_chat_completions_json_success(client, mock_router):
    """Test /v1/chat/completions endpoint non-streaming request."""
    settings = get_settings()
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.FREEAI_API_KEY}"},
        json={"model": "chat", "messages": [{"role": "user", "content": "Oi"}]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["choices"][0]["message"]["content"] == "Olá, mundo!"
    mock_router.acompletion.assert_called_once()


def test_embeddings_success(client, mock_router):
    """Test /v1/embeddings endpoint request."""
    settings = get_settings()
    response = client.post(
        "/v1/embeddings",
        headers={"Authorization": f"Bearer {settings.FREEAI_API_KEY}"},
        json={"model": "embed", "input": "teste"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"][0]["embedding"]) == 3
    mock_router.aembedding.assert_called_once()


def test_chat_completions_streaming_success(client, mock_router):
    """Test /v1/chat/completions endpoint with SSE streaming."""

    async def async_stream():
        yield {"choices": [{"delta": {"content": "Olá"}}]}
        yield {"choices": [{"delta": {"content": "!"}}]}

    mock_router.acompletion = AsyncMock(return_value=async_stream())
    settings = get_settings()

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.FREEAI_API_KEY}"},
        json={"model": "chat", "messages": [{"role": "user", "content": "Oi"}], "stream": True},
    )
    assert response.status_code == 200
    assert "data: " in response.text
    assert "data: [DONE]" in response.text
