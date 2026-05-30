from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openrouter_api_key: str = Field(
        default="",
        description="Primary OpenRouter API key (used when OPENROUTER_KEYS is empty)",
    )
    openrouter_keys: str = Field(
        default="",
        description="Comma-separated keys with optional daily quota: key1:50,key2:1000",
    )
    openrouter_api_base: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL",
    )
    or_site_url: str = Field(
        default="http://localhost:3000",
        description="HTTP-Referer for OpenRouter stats",
    )
    or_app_name: str = Field(default="GPTHub", description="X-Title for OpenRouter stats")
    openrouter_rpm_limit: int = Field(default=20, ge=1, le=120)
    openrouter_key_cooldown_seconds: float = Field(default=14400.0, ge=60.0, le=86400.0)
    openrouter_quota_timezone: str = Field(default="UTC")
    openrouter_timeout_seconds: float = Field(
        default=600.0,
        ge=5.0,
        le=3600.0,
        description="httpx timeout for OpenRouter requests",
    )
    openrouter_refresh_catalog_on_startup: bool = Field(
        default=True,
        description="On startup, fetch live free models from OpenRouter and rebuild fallback chains",
    )
    openrouter_catalog_persist_on_refresh: bool = Field(
        default=True,
        description="Write refreshed catalog to FREE_MODELS_CATALOG_PATH or packaged data file",
    )
    openrouter_catalog_text_limit: int = Field(default=4, ge=1, le=12)
    openrouter_catalog_vision_limit: int = Field(default=5, ge=1, le=12)
    openrouter_catalog_fail_on_refresh_error: bool = Field(
        default=False,
        description="If true, orchestrator fails startup when live catalog refresh fails",
    )
    openrouter_catalog_refresh_interval_hours: float = Field(
        default=0.0,
        ge=0.0,
        le=168.0,
        description="Periodic live catalog refresh interval; 0 disables background refresh",
    )
    openrouter_probe_on_refresh: bool = Field(
        default=True,
        description="Micro-probe head slug per catalog section after refresh",
    )
    openrouter_probe_max_models: int = Field(default=4, ge=1, le=8)
    openrouter_probe_delay_seconds: float = Field(default=1.5, ge=0.0, le=10.0)
    openrouter_catalog_denylist: str = Field(
        default="",
        description="Comma-separated extra model id slugs to exclude from scoring",
    )
    openrouter_bandit_enabled: bool = Field(
        default=True,
        description="Enable EMA bandit periodic chain resort",
    )
    openrouter_bandit_resort_interval_minutes: float = Field(default=30.0, ge=5.0, le=1440.0)
    openrouter_bandit_min_samples: int = Field(default=5, ge=1, le=100)
    openrouter_curator_merge_mode: Literal["overlay", "replace"] = Field(
        default="overlay",
        description="How curator manifest merges with heuristic catalog",
    )
    openrouter_model_ban_after_429: int = Field(default=3, ge=1, le=20)
    openrouter_model_ban_ttl_seconds: float = Field(default=3600.0, ge=60.0, le=86400.0)
    openrouter_curator_enabled: bool = Field(
        default=False,
        description="Run async LLM curator on startup to refine routing manifest",
    )
    openrouter_curator_model: str = Field(
        default="google/gemma-4-26b-a4b-it:free",
        description="Free OpenRouter model for curator structured JSON",
    )
    openrouter_curator_timeout: float = Field(default=60.0, ge=10.0, le=300.0)
    openrouter_curator_digest_limit: int = Field(default=50, ge=10, le=80)
    orchestrator_stream_fallback_max_attempts: int = Field(default=3, ge=1, le=12)
    orchestrator_admin_api_key: str = Field(
        default="",
        description="Bearer token for /v1/admin/*; defaults to orchestrator_api_key when empty",
    )
    orchestrator_api_key: str = Field(
        ...,
        description="Bearer token from clients (Open WebUI)",
    )
    auto_route_model: bool = Field(
        default=True,
        description="If true, override request model with rule-based router suggestion",
    )
    code_route_preference: Literal["local", "openrouter"] = Field(
        default="openrouter",
        description="For code/deep tasks: role key (prompt) differs; v4 uses OpenRouter chains only",
    )
    orchestrator_openrouter_fallback: bool = Field(
        default=True,
        description="Non-stream: retry with next model/key on 429/5xx",
    )
    orchestrator_fallback_max_attempts: int = Field(default=8, ge=1, le=24)
    model_roles_path: str | None = Field(default=None)
    role_prompts_path: str | None = Field(default=None)
    free_models_catalog_path: str | None = Field(
        default=None,
        description="Optional path to free_models_catalog.yaml",
    )
    default_text_model: str = Field(
        default="liquid/lfm-2.5-1.2b-instruct:free",
        description="Fallback slug when auto_route_model is false",
    )
    default_vision_model: str = Field(default="google/gemma-4-26b-a4b-it:free")
    log_level: str = Field(default="INFO")
    inject_request_datetime: bool = Field(default=True)
    orchestrator_clock_tz: str = Field(default="UTC")
    orchestrator_models_catalog: Literal["all", "single_public"] = Field(default="single_public")
    orchestrator_public_model_id: str = Field(default="gpt-hub", min_length=1)
    greeting_canned_response_enabled: bool = Field(default=False)
    greeting_canned_message: str = Field(default="Привет! Чем могу помочь?", min_length=1)
    orchestrator_strip_known_cot_preamble: bool = Field(default=False)
    orchestrator_request_reasoning_exclude: bool = Field(default=True)
    orchestrator_strip_reasoning_from_response: bool = Field(default=True)
    ingest_enabled: bool = Field(default=True)
    orchestrator_asr_base_url: str | None = Field(default=None)
    orchestrator_asr_api_key: str = Field(default="local-asr")
    orchestrator_asr_model: str = Field(default="whisper-1")
    ingest_pdf_max_bytes: int = Field(default=15_000_000, ge=1024, le=50_000_000)
    ingest_pdf_max_pages: int = Field(default=50, ge=1, le=500)
    ingest_fetch_max_bytes: int = Field(default=25_000_000, ge=1024, le=100_000_000)
    ingest_image_fetch_timeout: float = Field(default=60.0, ge=5.0, le=600.0)

    @field_validator("model_roles_path", "role_prompts_path", "free_models_catalog_path", mode="before")
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

    @field_validator("openrouter_api_key", mode="before")
    @classmethod
    def strip_or_key(cls, v: object) -> str:
        return str(v or "").strip()

    @model_validator(mode="after")
    def default_admin_api_key(self) -> Settings:
        if not self.orchestrator_admin_api_key.strip():
            self.orchestrator_admin_api_key = self.orchestrator_api_key
        return self

    def openrouter_catalog_denylist_list(self) -> list[str]:
        if not self.openrouter_catalog_denylist.strip():
            return []
        return [s.strip() for s in self.openrouter_catalog_denylist.split(",") if s.strip()]


def load_settings() -> Settings:
    return Settings()
