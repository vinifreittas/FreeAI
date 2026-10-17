import contextlib
import time
from collections.abc import AsyncGenerator
from typing import Any

import litellm

litellm.suppress_debug_info = True


class StreamResponse:
    """Async wrapper carrying diagnostic metadata for streaming response."""

    def __init__(self, gen: Any, provider: str = "", model: str = "", attempts: int = 0):
        self._gen = gen
        self._freeai_provider = provider
        self._freeai_model = model
        self._freeai_attempts = attempts

    def __aiter__(self):
        return self._gen.__aiter__()


def _attach_diag(obj: Any, provider: str, model: str, attempts: int) -> Any:
    with contextlib.suppress(AttributeError, TypeError):
        obj._freeai_provider, obj._freeai_model, obj._freeai_attempts = provider, model, attempts
    return obj


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

    def reset_cooldowns(self) -> None:
        """Clears all in-memory cooldowns and disabled models/providers."""
        self._cooldowns.clear(), self._disabled_models.clear(), self._disabled_providers.clear()

    def get_cooldown_status(self) -> dict[str, Any]:
        """Returns current active cooldowns and disabled models/providers."""
        now = time.time()
        active = {k: max(0, int(v - now)) for k, v in self._cooldowns.items() if v > now}
        return {
            "cooldowns": active,
            "disabled_models": sorted(self._disabled_models),
            "disabled_providers": sorted(self._disabled_providers),
        }

    def _is_target_available(self, target: Any) -> bool:
        litellm_model = getattr(target, "litellm_model", str(target))
        provider_id = getattr(target, "provider_id", litellm_model.split("/")[0] if "/" in litellm_model else "")
        target_id = getattr(target, "target_id", litellm_model)

        if (
            target_id in self._disabled_models
            or litellm_model in self._disabled_models
            or (provider_id and provider_id in self._disabled_providers)
        ):
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
            self._disabled_models.update({target_id, litellm_model})
            return

        if isinstance(exc, litellm.RateLimitError):
            daily_kw = ("quota", "daily", "per day", "rpd", "tpd")
            is_daily = any(k in str(exc).lower() for k in daily_kw)
            cooldown = self.daily_cooldown_seconds if is_daily else self.minute_cooldown_seconds
            self._cooldowns[litellm_model] = time.time() + cooldown
            return

        self._cooldowns[litellm_model] = time.time() + self.minute_cooldown_seconds

    def _get_target_list(self, model_name: str) -> list[Any]:
        if not self.catalog:
            return [model_name]
        if hasattr(self.catalog, "get_targets"):
            return self.catalog.get_targets(model_name)
        routes = getattr(self.catalog, "routes", self.catalog)
        return routes.get(model_name, []) if isinstance(routes, dict) else []

    def _prepare_call(self, default_route: str, kwargs: dict[str, Any]) -> tuple[str, list[Any]]:
        route_name = kwargs.get("model", default_route)
        targets = [t for t in self._get_target_list(route_name) if self._is_target_available(t)]
        if not targets:
            raise RuntimeError(f"Nenhum modelo disponível para a rota '{route_name}'")
        return route_name, targets

    async def acompletion(self, **kwargs: Any) -> Any:
        if not kwargs.get("stream", False):
            return await self._execute_sdk_func(litellm.acompletion, default_route="chat", **kwargs)

        route_name, targets = self._prepare_call("chat", kwargs)
        last_exc: Exception | None = None
        for attempt, target in enumerate(targets):
            call_kwargs = {**kwargs, "model": getattr(target, "litellm_model", str(target))}
            try:
                res = await litellm.acompletion(**call_kwargs)
                return StreamResponse(
                    self._wrap_stream(res, target),
                    getattr(target, "provider_id", ""),
                    call_kwargs["model"],
                    attempt,
                )
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

    def completion(self, **kwargs: Any) -> Any:
        return self._execute_sync_func(litellm.completion, default_route="chat", **kwargs)

    def embedding(self, **kwargs: Any) -> Any:
        return self._execute_sync_func(litellm.embedding, default_route="embed", **kwargs)

    async def aembedding(self, **kwargs: Any) -> Any:
        return await self._execute_sdk_func(litellm.aembedding, default_route="embed", **kwargs)

    async def aspeech(self, **kwargs: Any) -> Any:
        return await self._execute_sdk_func(litellm.aspeech, default_route="tts", **kwargs)

    async def atranscription(self, **kwargs: Any) -> Any:
        return await self._execute_sdk_func(litellm.atranscription, default_route="stt", **kwargs)

    def _execute_sync_func(self, sdk_func: Any, default_route: str = "default", **kwargs: Any) -> Any:
        route_name, targets = self._prepare_call(default_route, kwargs)
        last_exc: Exception | None = None
        for attempt, target in enumerate(targets):
            call_kwargs = {**kwargs, "model": getattr(target, "litellm_model", str(target))}
            try:
                res = sdk_func(**call_kwargs)
                return _attach_diag(res, getattr(target, "provider_id", ""), call_kwargs["model"], attempt)
            except Exception as exc:
                self._handle_execution_error(target, exc)
                if isinstance(exc, litellm.BadRequestError | litellm.InvalidRequestError):
                    raise
                last_exc = exc
        if last_exc:
            raise last_exc
        raise RuntimeError(f"Falha ao executar chamada para rota '{route_name}'")

    async def _execute_sdk_func(self, sdk_func: Any, default_route: str = "default", **kwargs: Any) -> Any:
        route_name, targets = self._prepare_call(default_route, kwargs)
        last_exc: Exception | None = None
        for attempt, target in enumerate(targets):
            call_kwargs = {**kwargs, "model": getattr(target, "litellm_model", str(target))}
            try:
                res = await sdk_func(**call_kwargs)
                return _attach_diag(res, getattr(target, "provider_id", ""), call_kwargs["model"], attempt)
            except Exception as exc:
                self._handle_execution_error(target, exc)
                if isinstance(exc, litellm.BadRequestError | litellm.InvalidRequestError):
                    raise
                last_exc = exc
        if last_exc:
            raise last_exc
        raise RuntimeError(f"Falha ao executar chamada para rota '{route_name}'")
