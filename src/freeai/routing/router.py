import os
from pathlib import Path
from typing import Any

from litellm import Router

from freeai.config import ProviderConfig, get_settings


def _build_litellm_params(
    provider: ProviderConfig,
    remote_model: str,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct standard parameters required by LiteLLM router models."""
    params: dict[str, Any] = {
        "model": f"{provider.id}/{remote_model}",
        "api_key": provider.api_key,
    }
    if provider.base_url:
        params["api_base"] = provider.base_url
    if extra_params:
        params.update(extra_params)
    return params


def build_router(config_path: Path | str | None = None) -> Router:
    """Build and initialize a LiteLLM Router instance using application settings."""
    settings = get_settings()

    # 1. Sync provider API keys into environment variables
    for provider in settings.providers:
        if provider.api_key and provider.api_key_env not in os.environ:
            os.environ[provider.api_key_env] = provider.api_key

    # 2. Build model list for backend models
    model_list = [
        {
            "model_name": model.id,
            "litellm_params": _build_litellm_params(provider, model.remote_model, model.default_params),
        }
        for provider in settings.providers
        for model in provider.models
    ]

    # 3. Append alias models
    for alias in settings.aliases:
        model, provider, _ = settings.resolve_alias(alias.alias)
        if model and provider:
            model_list.append(
                {
                    "model_name": alias.alias,
                    "litellm_params": _build_litellm_params(provider, model.remote_model, alias.override_params),
                }
            )

    # 4. Format fallbacks for all aliases and direct model IDs
    all_keys = {m.id for p in settings.providers for m in p.models} | {a.alias for a in settings.aliases}
    fallbacks = [{key: settings.get_fallbacks_for(key)} for key in all_keys if settings.get_fallbacks_for(key)]

    return Router(
        model_list=model_list,
        routing_strategy="usage-based-routing-v2",
        num_retries=3,
        allowed_fails=1,
        cooldown_time=60,
        fallbacks=fallbacks,
    )
