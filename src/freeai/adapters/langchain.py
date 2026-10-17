from typing import Any

from freeai.core import build_router_catalog, get_settings
from freeai.services import Router

try:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
except ImportError:
    BaseChatModel = object  # type: ignore
    AIMessage = object  # type: ignore
    ChatGeneration = object  # type: ignore
    ChatResult = object  # type: ignore


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


class ChatFreeAI(BaseChatModel):
    """LangChain chat model routing completions through FreeAI fallback chains."""

    model: str = "chat"
    router: Any = None

    def __init__(self, model: str = "chat", router: Any = None, **kwargs: Any) -> None:
        if BaseChatModel is object:
            raise ImportError("Para usar o adaptador LangChain, instale o pacote langchain-core: uv add langchain-core")
        super().__init__(model=model, router=router or get_default_router(), **kwargs)

    @property
    def _llm_type(self) -> str:
        return "freeai-chat"

    def _format_messages(self, messages: list[Any]) -> list[dict[str, str]]:
        formatted = []
        for msg in messages:
            role = getattr(msg, "type", "user")
            role_map = {"human": "user", "ai": "assistant", "system": "system"}
            formatted.append({"role": role_map.get(role, role), "content": str(getattr(msg, "content", ""))})
        return formatted

    def _generate(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> Any:
        router = self.router or get_default_router()
        formatted = self._format_messages(messages)
        call_kwargs = {**kwargs, "model": self.model, "messages": formatted}
        if stop:
            call_kwargs["stop"] = stop
        res = router.completion(**call_kwargs)
        content = res.choices[0].message.content or ""
        generation = ChatGeneration(message=AIMessage(content=content))
        return ChatResult(generations=[generation])

    async def _agenerate(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> Any:
        router = self.router or get_default_router()
        formatted = self._format_messages(messages)
        call_kwargs = {**kwargs, "model": self.model, "messages": formatted}
        if stop:
            call_kwargs["stop"] = stop
        res = await router.acompletion(**call_kwargs)
        content = res.choices[0].message.content or ""
        generation = ChatGeneration(message=AIMessage(content=content))
        return ChatResult(generations=[generation])
