import os
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 4000

    # Authentication
    FREEAI_API_KEY: str = ""

    # API Keys for upstream providers (Standard defaults)
    GEMINI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None

    # Path to models mapping YAML
    MODELS_CONFIG_PATH: Path = Path(__file__).parent / "models.yaml"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Returns a cached instance of application settings."""
    return Settings()


def get_all_provider_keys() -> dict[str, str]:
    """Retorna dinamicamente todas as chaves e variáveis de API de provedores presentes no .env e ambiente.

    Detecta variáveis terminadas em _API_KEY, _KEY, _API_BASE, _BASE ou _TOKEN.
    """
    keys: dict[str, str] = {}

    # 1. Varre arquivo .env local se existir
    env_path = Path(".env")
    if env_path.exists():
        env_vars = dotenv_values(env_path)
        for k, v in env_vars.items():
            if v and (
                k.endswith("_API_KEY")
                or k.endswith("_KEY")
                or k.endswith("_API_BASE")
                or k.endswith("_BASE")
                or k.endswith("_TOKEN")
            ):
                keys[k] = str(v)

    # 2. Varre variáveis no ambiente do sistema (sobrescreve se definidos)
    for k, v in os.environ.items():
        if v and (
            k.endswith("_API_KEY")
            or k.endswith("_KEY")
            or k.endswith("_API_BASE")
            or k.endswith("_BASE")
            or k.endswith("_TOKEN")
        ):
            keys[k] = v

    return keys
