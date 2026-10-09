import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from freeai.core.storage import load_vault


class DynamicBaseModel(BaseModel):
    """Base model allowing arbitrary extra fields."""

    model_config = ConfigDict(extra="allow")


class MetaConfig(DynamicBaseModel):
    version: str = "1.0.0"
    environment: str | None = None
    updated_at: str | None = None


class ModelConfig(DynamicBaseModel):
    id: str
    remote_model: str
    types: list[str] = Field(default_factory=list)
    specs: dict[str, Any] = Field(default_factory=dict)
    modalities: dict[str, Any] = Field(default_factory=dict)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    pricing_per_1m_tokens: dict[str, Any] | None = None
    default_params: dict[str, Any] = Field(default_factory=dict)


class ProviderConfig(DynamicBaseModel):
    id: str
    display_name: str
    api_key_env: str
    website_url: str | None = None
    protocol: str | None = None
    base_url: str | None = None
    rate_limits: dict[str, Any] | None = None
    models: list[ModelConfig] = Field(default_factory=list)

    @property
    def api_key(self) -> str | None:
        """Extract API key from vault if active and validated."""
        if not self.api_key_env:
            return None
        vault = load_vault()
        if self.api_key_env in vault:
            val = str(vault.get(self.api_key_env) or "").strip()
            if not val:
                os.environ.pop(self.api_key_env, None)
                return None
            if vault.get(f"{self.api_key_env}_VALIDATED") is False:
                return None
            os.environ[self.api_key_env] = val
            return val
        val = (os.getenv(self.api_key_env) or "").strip()
        return val or None


class AliasConfig(DynamicBaseModel):
    alias: str
    target_model_id: str | None = None
    description: str | None = None
    models_types_to_chain: list[str] = Field(default_factory=list)
    default_system_prompt: str | None = None
    override_params: dict[str, Any] = Field(default_factory=dict)


class RouterSettings(DynamicBaseModel):
    num_retries: int = 2
    minute_cooldown_seconds: int = 60
    daily_cooldown_seconds: int = 86400


class ResolvedTarget(BaseModel):
    target_id: str
    litellm_model: str
    provider_id: str
    api_key_env: str
    types: list[str] = Field(default_factory=list)


class ResolvedCatalog(BaseModel):
    routes: dict[str, list[ResolvedTarget]] = Field(default_factory=dict)

    def get_targets(self, route_or_alias: str) -> list[ResolvedTarget]:
        return self.routes.get(route_or_alias, [])

    def list_all_route_names(self) -> list[str]:
        return list(self.routes.keys())


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 4000
    FREEAI_API_KEY: str = ""
    SETTINGS_CONFIG_PATH: Path = Path(__file__).parent / "config.yaml"
    MODELS_CONFIG_PATH: Path = Path(__file__).parent / "config.yaml"

    meta: MetaConfig = Field(default_factory=MetaConfig)
    providers: list[ProviderConfig] = Field(default_factory=list)
    aliases: list[AliasConfig] = Field(default_factory=list)
    router_settings: RouterSettings = Field(default_factory=RouterSettings)

    model_config = SettingsConfigDict(
        extra="allow",
        case_sensitive=True,
    )

    @model_validator(mode="before")
    @classmethod
    def load_yaml_data(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        vault = load_vault()
        for k, v in vault.items():
            if isinstance(v, str) and v.strip():
                os.environ[k] = v.strip()
            elif not v:
                os.environ.pop(k, None)

        path_str = (
            data.get("SETTINGS_CONFIG_PATH")
            or data.get("MODELS_CONFIG_PATH")
            or vault.get("SETTINGS_CONFIG_PATH")
            or os.getenv("SETTINGS_CONFIG_PATH")
            or os.getenv("MODELS_CONFIG_PATH")
        )
        candidates = (Path(__file__).parent / "config.yaml", Path(__file__).parent / "settings.yaml")
        yaml_path = Path(path_str) if path_str else next((p for p in candidates if p.exists()), None)

        merged: dict[str, Any] = {}
        if yaml_path and yaml_path.exists():
            yaml_data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            if isinstance(yaml_data, dict):
                merged.update(yaml_data)

        merged.update(vault)
        merged.update(data)
        return merged

    def get_provider(self, provider_id: str) -> ProviderConfig | None:
        return next((p for p in self.providers if p.id == provider_id), None)

    def get_model_and_provider(self, model_id: str) -> tuple[ModelConfig | None, ProviderConfig | None]:
        return next(((m, p) for p in self.providers for m in p.models if m.id == model_id), (None, None))


def build_router_catalog(settings: Settings) -> ResolvedCatalog:
    """Builds the resolved catalog applying active provider filtering and type-matching fallback rules."""
    routes: dict[str, list[ResolvedTarget]] = {}

    active_targets: list[ResolvedTarget] = []
    for provider in settings.providers:
        if not provider.api_key:
            continue
        for model in provider.models:
            active_targets.append(
                ResolvedTarget(
                    target_id=model.id,
                    litellm_model=f"{provider.id}/{model.remote_model}",
                    provider_id=provider.id,
                    api_key_env=provider.api_key_env,
                    types=model.types,
                )
            )

    for target in active_targets:
        target_types_set = set(target.types)
        fallbacks = [c for c in active_targets if c.target_id != target.target_id and set(c.types) == target_types_set]
        routes[target.target_id] = [target, *fallbacks]

    for alias in settings.aliases:
        required_types_set = set(alias.models_types_to_chain)
        matching_targets = [c for c in active_targets if required_types_set.issubset(set(c.types))]
        if matching_targets:
            routes[alias.alias] = matching_targets

    return ResolvedCatalog(routes=routes)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    """Clears cache and reloads updated settings from vault."""
    get_settings.cache_clear()
    return get_settings()
