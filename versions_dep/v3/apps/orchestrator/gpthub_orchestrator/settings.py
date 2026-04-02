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
    orchestrator_request_reasoning_exclude: bool = Field(
        default=True,
        description="If true, merge reasoning.exclude into chat completion body for upstream (e.g. OpenRouter)",
    )
    orchestrator_strip_reasoning_from_response: bool = Field(
        default=True,
        description="If true, remove reasoning/thinking fields from JSON and stream chunks before the client",
    )
    ingest_enabled: bool = Field(
        default=True,
        description="If true, run perception ingest (PDF/audio) on last user message before routing",
    )
    orchestrator_asr_base_url: str | None = Field(
        default=None,
        description="OpenAI-compatible ASR base (e.g. http://host.docker.internal:8001/v1); unset skips audio ingest",
    )
    orchestrator_asr_api_key: str = Field(
        default="local-asr",
        description="Bearer for ASR when orchestrator transcribes audio parts",
    )
    orchestrator_asr_model: str = Field(
        default="cstr/whisper-large-v3-turbo-int8_float32",
        description="Model id for POST .../audio/transcriptions",
    )
    ingest_pdf_max_bytes: int = Field(default=15_000_000, ge=1024, le=50_000_000)
    ingest_pdf_max_pages: int = Field(default=50, ge=1, le=500)
    ingest_fetch_max_bytes: int = Field(default=25_000_000, ge=1024, le=100_000_000)
    ingest_image_fetch_timeout: float = Field(default=60.0, ge=5.0, le=600.0)

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

    @field_validator("orchestrator_asr_base_url", mode="before")
    @classmethod
    def empty_asr_url_to_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None


def load_settings() -> Settings:
    return Settings()
