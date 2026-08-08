import os
from pathlib import Path

import yaml
from litellm import Router

from freeai.config import get_all_provider_keys, get_settings


def build_router(config_path: Path | str | None = None) -> Router:
    """Carrega as configurações do models.yaml e instancia o litellm.Router.
    Args:
        config_path: Caminho opcional para o arquivo models.yaml.
                     Se omitido, utiliza o caminho padrão definido em Settings.

    Returns:
        Router: Instância configurada do litellm.Router.
    """
    settings = get_settings()
    target_path = Path(config_path) if config_path else settings.MODELS_CONFIG_PATH

    if not target_path.exists():
        raise FileNotFoundError(f"Arquivo de configuração de modelos não encontrado: {target_path}")

    # Injeção dinâmica e genérica de todas as chaves de API presentes no .env / ambiente
    provider_keys = get_all_provider_keys()
    for key_name, key_value in provider_keys.items():
        if key_value and key_name not in os.environ:
            os.environ[key_name] = key_value

    with open(target_path, encoding="utf-8") as f:
        raw_config = yaml.safe_load(f) or {}

    model_list = raw_config.get("model_list", [])
    router_settings = raw_config.get("router_settings", {})

    routing_strategy = router_settings.get("routing_strategy", "usage-based-routing-v2")
    num_retries = router_settings.get("num_retries", 3)
    allowed_fails = router_settings.get("allowed_fails", 1)
    cooldown_time = router_settings.get("cooldown_time", 60)
    fallbacks = router_settings.get("fallbacks", [])

    return Router(
        model_list=model_list,
        routing_strategy=routing_strategy,
        num_retries=num_retries,
        allowed_fails=allowed_fails,
        cooldown_time=cooldown_time,
        fallbacks=fallbacks,
    )
