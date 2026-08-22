import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- BASE & DYNAMIC MODELS ---


class DynamicBaseModel(BaseModel):
    """Base model allowing arbitrary extra fields without validation errors."""

    model_config = ConfigDict(extra="allow")


class MetaConfig(DynamicBaseModel):
    version: str = "1.0.0"


# Empty container aliases to eliminate redundant class boilerplate
GlobalDefaults = DynamicBaseModel
CacheSettings = DynamicBaseModel
RateLimits = DynamicBaseModel
PricingConfig = DynamicBaseModel
ModelCapabilities = DynamicBaseModel
ModelModalities = DynamicBaseModel
ModelSpecs = DynamicBaseModel

# --- DOMAIN MODELS ---


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
        """Dynamically extract the API key from the environment."""
        return os.getenv(self.api_key_env) if self.api_key_env else None


class AliasConfig(DynamicBaseModel):
    alias: str
    target_model_id: str
    description: str | None = None
    default_system_prompt: str | None = None
    override_params: dict[str, Any] = Field(default_factory=dict)


class RouterSettings(DynamicBaseModel):
    fallbacks: dict[str, list[str]] = Field(default_factory=dict)


# --- CENTRAL CONFIGURATION ---


class Settings(BaseSettings):
    # Environment variables
    HOST: str = "0.0.0.0"
    PORT: int = 4000
    FREEAI_API_KEY: str = ""
    MODELS_CONFIG_PATH: Path = Path(__file__).parent / "models.yaml"

    # YAML Sections
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

    @model_validator(mode="before")
    @classmethod
    def load_yaml_data(cls, data: Any) -> Any:
        """Merge YAML contents into configuration data before Pydantic validation."""
        if not isinstance(data, dict):
            return data

        yaml_path_str = data.get("MODELS_CONFIG_PATH") or os.getenv("MODELS_CONFIG_PATH")
        yaml_path = Path(yaml_path_str) if yaml_path_str else Path(__file__).parent / "models.yaml"

        if yaml_path.exists():
            yaml_data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            if isinstance(yaml_data, dict):
                # Reverse merge: YAML populates missing keys without overwriting explicit inputs
                return yaml_data | data
        return data

    # Helper methods using expressions and generators
    def get_provider(self, provider_id: str) -> ProviderConfig | None:
        """Retrieve a provider configuration by its ID."""
        return next((p for p in self.providers if p.id == provider_id), None)

    def get_model_and_provider(self, model_id: str) -> tuple[ModelConfig | None, ProviderConfig | None]:
        """Find a model and its associated parent provider."""
        return next(
            ((m, p) for p in self.providers for m in p.models if m.id == model_id),
            (None, None),
        )

    def resolve_alias(self, alias_name: str) -> tuple[ModelConfig | None, ProviderConfig | None, AliasConfig | None]:
        """Resolve an alias to its target model, provider, and override settings."""
        alias = next((a for a in self.aliases if a.alias == alias_name), None)
        if not alias:
            return None, None, None

        model, provider = self.get_model_and_provider(alias.target_model_id)
        if model and provider:
            return model, provider, alias
        return None, None, None

    def get_fallbacks_for(self, target_id: str) -> list[str]:
        """Return explicit and dynamic similarity-based fallbacks for a given model or alias ID."""
        explicit = self.router_settings.fallbacks.get(target_id, [])

        model, _ = self.get_model_and_provider(target_id)
        if not model:
            model, _, _ = self.resolve_alias(target_id)

        target_type = model.type if model and model.type else "chat"

        # Discover dynamic fallback candidates by matching capability/type
        dynamic = [
            m.id
            for p in self.providers
            for m in p.models
            if m.id != target_id and (m.type == target_type or (not m.type and target_type == "chat"))
        ]

        return list(dict.fromkeys(explicit + dynamic))


@lru_cache
def get_settings() -> Settings:
    """Cached singleton instance of the configuration settings."""
    return Settings()
