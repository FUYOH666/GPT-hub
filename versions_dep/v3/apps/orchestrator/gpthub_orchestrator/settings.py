from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    litellm_base_url: str = Field(
        ...,
        description="LiteLLM proxy base URL without trailing slash",
    )
    orchestrator_api_key: str = Field(
        ...,
        description="Bearer token from clients (same as LITELLM_MASTER_KEY for WebUI)",
    )
    litellm_timeout_seconds: float = Field(
        default=600.0,
        ge=5.0,
        le=3600.0,
        description="httpx timeout (connect/read/write/pool) for LiteLLM; raise for long RAG/PDF streams",
    )
    auto_route_model: bool = Field(
        default=True,
        description="If true, override request model with rule-based router suggestion (GPTHub default)",
    )
    code_route_preference: Literal["local", "openrouter"] = Field(
        default="local",
        description="For code/deep tasks: prefer local gpt-hub-turbo vs OpenRouter free chain",
    )
    orchestrator_litellm_fallback: bool = Field(
        default=True,
        description="Non-stream: retry LiteLLM with next alias in chain on 429/503",
    )
    orchestrator_fallback_max_attempts: int = Field(default=4, ge=1, le=8)
    model_roles_path: str | None = Field(
        default=None,
        description="Optional path to model_roles.yaml (default: packaged data)",
    )
    default_text_model: str = Field(default="gpt-hub-strong")
    default_vision_model: str = Field(default="gpt-hub-vision")
    default_code_heavy_model: str = Field(default="gpt-hub-turbo")
    log_level: str = Field(default="INFO")


def load_settings() -> Settings:
    return Settings()
