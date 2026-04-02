"""Load role → LiteLLM alias chains from packaged YAML."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

_PACKAGE_DATA = Path(__file__).resolve().parent / "data" / "model_roles.yaml"

# Keys in model_roles.yaml roles:
ROLE_FAST_TEXT: Final = "fast_text"
ROLE_REASONING_LOCAL: Final = "reasoning_code_local"
ROLE_REASONING_OPENROUTER: Final = "reasoning_code_openrouter"
ROLE_VISION: Final = "vision_general"
ROLE_DOC: Final = "doc_synthesis"


class RoleAliases(BaseModel):
    aliases: list[str] = Field(min_length=1)

    @field_validator("aliases")
    @classmethod
    def non_empty_strings(cls, v: list[str]) -> list[str]:
        out = [a.strip() for a in v if str(a).strip()]
        if not out:
            raise ValueError("aliases must contain at least one non-empty id")
        return out


class ModelRolesFile(BaseModel):
    version: int = 1
    roles: dict[str, RoleAliases]


@lru_cache(maxsize=1)
def load_model_roles(path: str | None = None) -> ModelRolesFile:
    """Load registry from ``path`` or default packaged ``model_roles.yaml``."""
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


def aliases_for_role(registry: ModelRolesFile, role_key: str) -> list[str]:
    entry = registry.roles.get(role_key)
    if entry is None:
        raise KeyError(f"unknown model role: {role_key}")
    return list(entry.aliases)
