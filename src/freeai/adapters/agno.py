from typing import Any

from freeai.core import build_router_catalog, get_settings
from freeai.services import Router

try:
    from agno.models.litellm import LiteLLM
except ImportError:
    LiteLLM = object  # type: ignore


def get_default_router() -> Router:
    """Creates a default Router initialized with current vault and environment settings."""
    settings = get_settings()
    catalog = build_router_catalog(settings)
    return Router(
        catalog=catalog,
        minute_cooldown_seconds=settings.router_settings.minute_cooldown_seconds,
        daily_cooldown_seconds=settings.router_settings.daily_cooldown_seconds,
        num_retries=settings.router_settings.num_retries,
    )


class FreeAIChat(LiteLLM):
    """Agno model adapter routing calls through FreeAI intelligent fallback."""

    def __init__(self, id: str = "chat", router: Router | None = None, **kwargs: Any) -> None:
        if LiteLLM is object:
            raise ImportError("Para usar o adaptador Agno, instale o pacote agno: uv add agno")
        client = router or get_default_router()
        super().__init__(id=id, client=client, **kwargs)
