import os
from pathlib import Path

from litellm import Router

from freeai.config import get_settings


def build_router(config_path: Path | str | None = None) -> Router:
    """Carrega as configurações dos modelos/provedores mapeados no Settings
    e instancia o litellm.Router injetando sempre o ID do provedor no início.
    """
    settings = get_settings()

    # 1. Injeta chaves de API detectadas nos provedores no ambiente
    for provider in settings.providers:
        api_key = provider.api_key
        if api_key and provider.api_key_env not in os.environ:
            os.environ[provider.api_key_env] = api_key

    model_list: list[dict] = []

    # 2. Constrói a model_list para Modelos Backend
    for provider in settings.providers:
        for model in provider.models:
            # Injeção direta: <provider_id>/<remote_model>
            litellm_model = f"{provider.id}/{model.remote_model}"

            litellm_params = {
                "model": litellm_model,
                "api_key": provider.api_key,
            }
            if provider.base_url:
                litellm_params["api_base"] = provider.base_url

            if model.default_params:
                litellm_params.update(model.default_params)

            model_list.append(
                {
                    "model_name": model.id,
                    "litellm_params": litellm_params,
                }
            )

    # 3. Constrói a model_list para Aliases
    for alias in settings.aliases:
        target_model, target_provider, _ = settings.resolve_alias(alias.alias)
        if not target_model or not target_provider:
            continue

        # Injeção direta: <provider_id>/<remote_model>
        litellm_model = f"{target_provider.id}/{target_model.remote_model}"

        litellm_params = {
            "model": litellm_model,
            "api_key": target_provider.api_key,
        }
        if target_provider.base_url:
            litellm_params["api_base"] = target_provider.base_url

        if alias.override_params:
            litellm_params.update(alias.override_params)

        model_list.append(
            {
                "model_name": alias.alias,
                "litellm_params": litellm_params,
            }
        )

    # 4. Formata Fallbacks
    fallbacks_config = settings.router_settings.fallbacks or {}
    fallbacks = [{source_model: target_list} for source_model, target_list in fallbacks_config.items()]

    return Router(
        model_list=model_list,
        routing_strategy="usage-based-routing-v2",
        num_retries=3,
        allowed_fails=1,
        cooldown_time=60,
        fallbacks=fallbacks,
    )
