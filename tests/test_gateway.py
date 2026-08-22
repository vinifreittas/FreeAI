from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from freeai.config import get_settings
from freeai.gateway.server import create_app


def test_list_models_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "FREEAI_API_KEY", "")

    mock_router = MagicMock()
    mock_router.model_list = [
        {"model_name": "chat"},
        {"model_name": "coder"},
        {"model_name": "gemini-3.5-flash"},
    ]

    app = create_app(router_instance=mock_router)
    client = TestClient(app)

    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    model_ids = [m["id"] for m in data["data"]]
    assert "chat" in model_ids
    assert "coder" in model_ids
