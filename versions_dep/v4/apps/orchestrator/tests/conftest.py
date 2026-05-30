import pytest

from gpthub_orchestrator.model_registry import load_model_roles
from gpthub_orchestrator.openrouter.catalog import (
    _load_free_models_catalog_from_disk,
    clear_runtime_catalog,
)
from gpthub_orchestrator.openrouter.routing_manifest import reset_curator_state
from gpthub_orchestrator.role_prompts import load_role_prompts


@pytest.fixture(autouse=True)
def clear_orchestrator_yaml_caches():
    load_model_roles.cache_clear()
    load_role_prompts.cache_clear()
    clear_runtime_catalog()
    reset_curator_state()
    _load_free_models_catalog_from_disk.cache_clear()
    yield
    load_model_roles.cache_clear()
    load_role_prompts.cache_clear()
    clear_runtime_catalog()
    reset_curator_state()
    _load_free_models_catalog_from_disk.cache_clear()
