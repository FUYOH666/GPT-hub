"""Load role → OpenRouter model chains from YAML + free catalog."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, Field, model_validator

from gpthub_orchestrator.openrouter.catalog import FreeModelsCatalog, load_free_models_catalog

logger = logging.getLogger(__name__)

_PACKAGE_DATA = Path(__file__).resolve().parent / "data" / "model_roles.yaml"

ROLE_FAST_TEXT_CHAT: Final = "fast_text_chat"
ROLE_FAST_TEXT: Final = "fast_text"
ROLE_REASONING_LOCAL: Final = "reasoning_code_local"
ROLE_REASONING_OPENROUTER: Final = "reasoning_code_openrouter"
ROLE_VISION: Final = "vision_general"
ROLE_DOC: Final = "doc_synthesis"

MODEL_ROLE_KEYS: Final[frozenset[str]] = frozenset(
    {
        ROLE_FAST_TEXT_CHAT,
        ROLE_FAST_TEXT,
        ROLE_DOC,
        ROLE_REASONING_LOCAL,
        ROLE_REASONING_OPENROUTER,
        ROLE_VISION,
    }
)


class RoleChain(BaseModel):
    chain: str | None = None
    aliases: list[str] | None = None

    @model_validator(mode="after")
    def chain_or_aliases(self) -> RoleChain:
        has_chain = bool(self.chain and str(self.chain).strip())
        has_aliases = bool(self.aliases and [a for a in self.aliases if str(a).strip()])
        if has_chain == has_aliases:
            raise ValueError("each role must have exactly one of chain or aliases")
        return self


class ModelRolesFile(BaseModel):
    version: int = 2
    roles: dict[str, RoleChain]

    def model_post_init(self, __context: object) -> None:
        missing = MODEL_ROLE_KEYS - set(self.roles.keys())
        if missing:
            raise ValueError(f"model_roles.yaml missing roles: {sorted(missing)}")


@lru_cache(maxsize=1)
def load_model_roles(path: str | None = None) -> ModelRolesFile:
    p = Path(path) if path else _PACKAGE_DATA
    if not p.is_file():
        raise FileNotFoundError(f"model roles file not found: {p}")
    raw = p.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("model_roles.yaml must parse to a mapping")
    parsed = ModelRolesFile.model_validate(data)
    logger.info("model_roles_loaded path=%s version=%s roles=%s", p, parsed.version, list(parsed.roles))
    return parsed


def resolve_role_chain(
    registry: ModelRolesFile,
    role_key: str,
    catalog: FreeModelsCatalog,
) -> list[str]:
    entry = registry.roles.get(role_key)
    if entry is None:
        raise KeyError(f"unknown model role: {role_key}")
    if entry.chain:
        resolved = catalog.resolve_chain(entry.chain)
    elif entry.aliases:
        resolved = [a.strip() for a in entry.aliases if str(a).strip()]
    else:
        raise ValueError(f"role {role_key} has no chain or aliases")
    if not resolved:
        raise ValueError(f"role {role_key} resolved to empty chain")
    return resolved


def aliases_for_role(
    registry: ModelRolesFile,
    role_key: str,
    *,
    catalog_path: str | None = None,
) -> list[str]:
    catalog = load_free_models_catalog(catalog_path)
    return resolve_role_chain(registry, role_key, catalog)
