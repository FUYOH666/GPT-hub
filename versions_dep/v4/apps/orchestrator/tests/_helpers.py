"""Shared test helpers."""

from __future__ import annotations

from gpthub_orchestrator.openrouter.client import OpenRouterClient
from gpthub_orchestrator.settings import Settings


def wire_app_state(app, mock_inner, **settings_kwargs) -> Settings:
    settings = Settings(
        openrouter_api_key="or-test-key",
        orchestrator_api_key="test-key",
        **settings_kwargs,
    )
    app.state.settings = settings
    app.state.http = mock_inner
    app.state.openrouter = OpenRouterClient(mock_inner, settings)
    return settings
