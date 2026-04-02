from typing import Literal

from pydantic import Field, field_validator
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
    role_prompts_path: str | None = Field(
        default=None,
        description="Optional path to role_prompts.yaml (default: packaged data)",
    )
    default_text_model: str = Field(default="gpt-hub-strong")
    default_vision_model: str = Field(default="gpt-hub-vision")
    default_code_heavy_model: str = Field(default="gpt-hub-turbo")
    log_level: str = Field(default="INFO")
    inject_request_datetime: bool = Field(
        default=True,
        description="Prepend server date/time to system message so the model can answer 'what time is it'",
    )
    orchestrator_clock_tz: str = Field(
        default="UTC",
        description="IANA timezone for inject_request_datetime (e.g. Europe/Moscow, UTC)",
    )
    orchestrator_models_catalog: Literal["all", "single_public"] = Field(
        default="single_public",
        description="GET /v1/models: expose all LiteLLM aliases or a single public facade id for Open WebUI",
    )
    orchestrator_public_model_id: str = Field(
        default="gpt-hub",
        min_length=1,
        description="Public model id shown in UI when catalog is single_public; must not be a LiteLLM alias",
    )
    greeting_canned_response_enabled: bool = Field(
        default=True,
        description="If true, greeting_or_tiny without images returns a fixed reply without calling LiteLLM",
    )
    greeting_canned_message: str = Field(
        default="Привет! Чем могу помочь?",
        min_length=1,
        description="Assistant text for canned greeting short-circuit",
    )
    orchestrator_strip_known_cot_preamble: bool = Field(
        default=False,
        description="If true, non-stream responses may strip known CoT preambles from assistant content (last resort)",
    )

    @field_validator("model_roles_path", "role_prompts_path", mode="before")
    @classmethod
    def empty_str_paths_to_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @field_validator("orchestrator_public_model_id", mode="after")
    @classmethod
    def strip_public_model_id(cls, v: str) -> str:
        return v.strip()

    @field_validator("greeting_canned_message", mode="after")
    @classmethod
    def strip_canned_message(cls, v: str) -> str:
        return v.strip()


def load_settings() -> Settings:
    return Settings()
