import time
from collections.abc import AsyncGenerator
from typing import Any

import litellm

litellm.suppress_debug_info = True


class Router:
    """Resilient LLM Routing engine managing in-memory cooldowns and LiteLLM fallback chains."""

    def __init__(
        self,
        catalog: Any = None,
        minute_cooldown_seconds: int = 60,
        daily_cooldown_seconds: int = 86400,
        num_retries: int = 2,
    ):
        self.catalog = catalog
        self.minute_cooldown_seconds = minute_cooldown_seconds
        self.daily_cooldown_seconds = daily_cooldown_seconds
        self.num_retries = num_retries
        self._cooldowns: dict[str, float] = {}
        self._disabled_models: set[str] = set()
        self._disabled_providers: set[str] = set()

    def _is_target_available(self, target: Any) -> bool:
        litellm_model = getattr(target, "litellm_model", str(target))
        provider_id = getattr(target, "provider_id", litellm_model.split("/")[0] if "/" in litellm_model else "")
        target_id = getattr(target, "target_id", litellm_model)

        if target_id in self._disabled_models or litellm_model in self._disabled_models:
            return False
        if provider_id and provider_id in self._disabled_providers:
            return False

        now = time.time()
        if litellm_model in self._cooldowns:
            if now < self._cooldowns[litellm_model]:
                return False
            del self._cooldowns[litellm_model]
        return True

    def _handle_execution_error(self, target: Any, exc: Exception) -> None:
        litellm_model = getattr(target, "litellm_model", str(target))
        provider_id = getattr(target, "provider_id", litellm_model.split("/")[0] if "/" in litellm_model else "")
        target_id = getattr(target, "target_id", litellm_model)

        if isinstance(exc, litellm.BadRequestError | litellm.InvalidRequestError):
            return

        if isinstance(exc, litellm.AuthenticationError):
            if provider_id:
                self._disabled_providers.add(provider_id)
            return

        if isinstance(exc, litellm.NotFoundError):
            self._disabled_models.add(target_id)
            self._disabled_models.add(litellm_model)
            return

        if isinstance(exc, litellm.RateLimitError):
            msg = str(exc).lower()
            daily_keywords = ["quota", "daily", "per day", "rpd", "tpd"]
            if any(kw in msg for kw in daily_keywords):
                self._cooldowns[litellm_model] = time.time() + self.daily_cooldown_seconds
            else:
                self._cooldowns[litellm_model] = time.time() + self.minute_cooldown_seconds
            return

        self._cooldowns[litellm_model] = time.time() + self.minute_cooldown_seconds

    def _get_target_list(self, model_name: str) -> list[Any]:
        if not self.catalog:
            return [model_name]
        if hasattr(self.catalog, "get_targets"):
            targets = self.catalog.get_targets(model_name)
        elif hasattr(self.catalog, "routes") and isinstance(self.catalog.routes, dict):
            targets = self.catalog.routes.get(model_name, [])
        elif isinstance(self.catalog, dict):
            targets = self.catalog.get(model_name, [])
        else:
            targets = []
        return targets

    async def acompletion(self, **kwargs: Any) -> Any:
        route_name = kwargs.get("model", "chat")
        targets = [t for t in self._get_target_list(route_name) if self._is_target_available(t)]

        if not targets:
            raise RuntimeError(f"Nenhum modelo disponível para a rota '{route_name}'")

        last_exc: Exception | None = None
        is_stream = kwargs.get("stream", False)

        for target in targets:
            call_kwargs = dict(kwargs)
            call_kwargs["model"] = getattr(target, "litellm_model", str(target))

            if is_stream:
                try:
                    response = await litellm.acompletion(**call_kwargs)
                    return self._wrap_stream(response, target)
                except Exception as exc:
                    self._handle_execution_error(target, exc)
                    if isinstance(exc, litellm.BadRequestError | litellm.InvalidRequestError):
                        raise
                    last_exc = exc
                    continue

            try:
                return await litellm.acompletion(**call_kwargs)
            except Exception as exc:
                self._handle_execution_error(target, exc)
                if isinstance(exc, litellm.BadRequestError | litellm.InvalidRequestError):
                    raise
                last_exc = exc

        if last_exc:
            raise last_exc
        raise RuntimeError(f"Falha ao executar acompletion para rota '{route_name}'")

    async def _wrap_stream(self, stream_response: Any, target: Any) -> AsyncGenerator[Any, None]:
        try:
            async for chunk in stream_response:
                yield chunk
        except Exception as exc:
            self._handle_execution_error(target, exc)
            raise

    async def aembedding(self, **kwargs: Any) -> Any:
        return await self._execute_sdk_func(litellm.aembedding, default_route="embed", **kwargs)

    async def aspeech(self, **kwargs: Any) -> Any:
        return await self._execute_sdk_func(litellm.aspeech, default_route="tts", **kwargs)

    async def atranscription(self, **kwargs: Any) -> Any:
        return await self._execute_sdk_func(litellm.atranscription, default_route="stt", **kwargs)

    async def _execute_sdk_func(self, sdk_func: Any, default_route: str = "default", **kwargs: Any) -> Any:
        route_name = kwargs.get("model", default_route)
        targets = [t for t in self._get_target_list(route_name) if self._is_target_available(t)]

        if not targets:
            raise RuntimeError(f"Nenhum modelo disponível para a rota '{route_name}'")

        last_exc: Exception | None = None
        for target in targets:
            call_kwargs = dict(kwargs)
            call_kwargs["model"] = getattr(target, "litellm_model", str(target))
            try:
                return await sdk_func(**call_kwargs)
            except Exception as exc:
                self._handle_execution_error(target, exc)
                if isinstance(exc, litellm.BadRequestError | litellm.InvalidRequestError):
                    raise
                last_exc = exc

        if last_exc:
            raise last_exc
        raise RuntimeError(f"Falha ao executar chamada para rota '{route_name}'")
