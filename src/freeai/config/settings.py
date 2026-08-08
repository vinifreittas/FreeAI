import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# =========================================================================
# YAML-BASED DYNAMIC CONFIGURATION MODELS
# =========================================================================


class DynamicBaseModel(BaseModel):
    """Base model that allows adding any new property without breaking."""

    model_config = ConfigDict(extra="allow")


class MetaConfig(DynamicBaseModel):
    version: str = "1.0.0"


class GlobalDefaults(DynamicBaseModel):
    pass


class CacheSettings(DynamicBaseModel):
    pass


class RateLimits(DynamicBaseModel):
    pass


class PricingConfig(DynamicBaseModel):
    pass


class ModelCapabilities(DynamicBaseModel):
    pass


class ModelModalities(DynamicBaseModel):
    pass


class ModelSpecs(DynamicBaseModel):
    pass


class ModelConfig(DynamicBaseModel):
    id: str
    remote_model: str
    type: str | None = None
    specs: ModelSpecs = Field(default_factory=ModelSpecs)
    modalities: ModelModalities = Field(default_factory=ModelModalities)
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)
    pricing_per_1m_tokens: PricingConfig | None = None
    default_params: dict[str, Any] = Field(default_factory=dict)


class ProviderConfig(DynamicBaseModel):
    id: str
    display_name: str
    api_key_env: str
    website_url: str | None = None
    protocol: str | None = None
    base_url: str | None = None
    rate_limits: RateLimits | None = None
    models: list[ModelConfig] = Field(default_factory=list)

    @property
    def api_key(self) -> str | None:
        """Extrai dinamicamente a chave de API do ambiente usando o nome configurado em `api_key_env`."""
        return os.getenv(self.api_key_env) if self.api_key_env else None


class AliasConfig(DynamicBaseModel):
    alias: str
    target_model_id: str
    description: str | None = None
    default_system_prompt: str | None = None
    override_params: dict[str, Any] = Field(default_factory=dict)


class RouterSettings(DynamicBaseModel):
    fallbacks: dict[str, list[str]] = Field(default_factory=dict)


# =========================================================================
# CENTRAL CONFIGURATION (Settings)
# =========================================================================


class Settings(BaseSettings):
    # --- ENVIRONMENT / SERVER VARIABLES ---
    HOST: str = "0.0.0.0"
    PORT: int = 4000
    FREEAI_API_KEY: str = ""
    MODELS_CONFIG_PATH: Path = Path(__file__).parent / "models.yaml"

    # --- YAML-LOADED SECTIONS ---
    meta: MetaConfig = Field(default_factory=MetaConfig)
    global_defaults: GlobalDefaults = Field(default_factory=GlobalDefaults)
    cache_settings: CacheSettings = Field(default_factory=CacheSettings)
    providers: list[ProviderConfig] = Field(default_factory=list)
    aliases: list[AliasConfig] = Field(default_factory=list)
    router_settings: RouterSettings = Field(default_factory=RouterSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
        case_sensitive=True,
    )

    def __init__(self, **values: Any):
        super().__init__(**values)
        load_dotenv()

    @model_validator(mode="before")
    @classmethod
    def load_yaml_data(cls, data: Any) -> Any:
        """Load and automatically merge YAML content into configuration before validation."""
        if isinstance(data, dict):
            yaml_path_str = data.get("MODELS_CONFIG_PATH") or os.getenv("MODELS_CONFIG_PATH")
            yaml_path = Path(yaml_path_str) if yaml_path_str else Path(__file__).parent / "models.yaml"

            if yaml_path.exists():
                with open(yaml_path, encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f) or {}
                    if isinstance(yaml_data, dict):
                        for key, value in yaml_data.items():
                            if key not in data or data[key] is None:
                                data[key] = value
        return data

    # --- APPLICATION HELPERS ---

    def get_provider(self, provider_id: str) -> ProviderConfig | None:
        """Get provider configurations by ID."""
        for provider in self.providers:
            if provider.id == provider_id:
                return provider
        return None

    def get_model_and_provider(self, model_id: str) -> tuple[ModelConfig | None, ProviderConfig | None]:
        """Find model and its parent provider."""
        for provider in self.providers:
            for model in provider.models:
                if model.id == model_id:
                    return model, provider
        return None, None

    def resolve_alias(self, alias_name: str) -> tuple[ModelConfig | None, ProviderConfig | None, AliasConfig | None]:
        """Resolve alias returning final model, provider, and alias overrides."""
        for alias in self.aliases:
            if alias.alias == alias_name:
                model, provider = self.get_model_and_provider(alias.target_model_id)
                if model and provider:
                    return model, provider, alias
        return None, None, None

    def get_fallbacks_for(self, target_id: str) -> list[str]:
        """Return the fallback list configured in YAML for a model or alias."""
        return self.router_settings.fallbacks.get(target_id, [])


@lru_cache
def get_settings() -> Settings:
    """Cached, globally accessible singleton instance."""
    return Settings()
