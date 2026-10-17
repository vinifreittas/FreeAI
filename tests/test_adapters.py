from unittest.mock import MagicMock

import pytest

from freeai.adapters import ChatFreeAI, FreeAIChat
from freeai.services import Router


def test_agno_adapter_initialization():
    mock_router = MagicMock(spec=Router)
    model = FreeAIChat(id="coder", router=mock_router)
    assert model.id == "coder"
    assert model.get_client() is mock_router


def test_agno_adapter_default_router():
    model = FreeAIChat(id="chat")
    assert model.id == "chat"
    assert isinstance(model.get_client(), Router)


def test_langchain_adapter_import_guard():
    # Since langchain-core is not installed in the dev environment,
    # attempting to initialize ChatFreeAI should raise a helpful ImportError.
    with pytest.raises(ImportError, match="langchain-core"):
        ChatFreeAI(model="chat")
