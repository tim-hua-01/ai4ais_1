"""Configuration loading for the multi-model comparison panel.

All model and backend definitions live in a YAML file (``config/models.yaml`` by
default, override with the ``AI4AIS_CONFIG`` env var). This module parses that
file into typed, resolved dataclasses so the rest of the app never touches raw
dicts. The two public entry points are :class:`AppConfig` and :func:`load_config`.

Supports the same fields used by typical multi-backend LLM clients: backend,
model_name, reasoning_effort, thinking_budget_tokens, openrouter_provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

# Reasoning styles understood by the API client layer. See config/models.yaml for
# what each one emits on the wire.
ReasoningStyle = Literal["effort", "openrouter", "adaptive", "budget", "none"]

BackendType = Literal["openai", "anthropic"]

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "models.yaml"

# Sentinel meaning "fall back to the model's configured reasoning_effort".
DEFAULT_EFFORT = "default"


@dataclass(frozen=True)
class BackendConfig:
    """A provider: where requests go and how reasoning effort is encoded."""

    name: str
    type: BackendType
    api_key_env: str
    reasoning_style: ReasoningStyle = "none"
    base_url: str | None = None  # required for openai-type backends
    max_tokens_param: str = "max_tokens"
    extra_headers: dict[str, str] = field(default_factory=dict)

    @property
    def api_key(self) -> str | None:
        return os.getenv(self.api_key_env)


@dataclass(frozen=True)
class ModelConfig:
    """A single selectable model, fully resolved against its backend + defaults."""

    id: str
    label: str
    backend: BackendConfig
    model_name: str
    reasoning_effort: str | None = None
    reasoning_style: ReasoningStyle = "none"
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    thinking_budget_tokens: int | None = None
    openrouter_provider: str | None = None
    timeout: float = 180.0

    def resolved_effort(self, override: str | None) -> str | None:
        """The effort to use for a request, given an optional per-panel override.

        ``override`` of ``None`` or ``"default"`` keeps the model's configured
        effort; anything else (including ``"none"``) wins.
        """
        if override is None or override == DEFAULT_EFFORT:
            return self.reasoning_effort
        return override


@dataclass(frozen=True)
class AppConfig:
    """Everything the app needs at runtime, parsed from YAML."""

    models: dict[str, ModelConfig]
    backends: dict[str, BackendConfig]
    default_panel_models: list[str]
    panel_count: int
    reasoning_effort_options: list[str]

    def model_summaries(self) -> list[dict[str, Any]]:
        """Compact, JSON-safe model list for the frontend (``/api/models``)."""
        summaries = []
        for model in self.models.values():
            # Always include the model's own default effort in its dropdown so a
            # configured value that isn't in the global option list still shows.
            efforts = list(self.reasoning_effort_options)
            if model.reasoning_effort and model.reasoning_effort not in efforts:
                efforts.append(model.reasoning_effort)
            summaries.append(
                {
                    "id": model.id,
                    "label": model.label,
                    "backend": model.backend.name,
                    "model_name": model.model_name,
                    "reasoning_effort": model.reasoning_effort,
                    "reasoning_style": model.reasoning_style,
                    "available_efforts": efforts,
                    "api_key_env": model.backend.api_key_env,
                    "configured": model.backend.api_key is not None,
                }
            )
        return summaries


def _coalesce(*values: Any) -> Any:
    """First non-None value, else None."""
    for value in values:
        if value is not None:
            return value
    return None


def load_config(path: str | os.PathLike[str] | None = None) -> AppConfig:
    """Load and resolve the YAML config into typed dataclasses.

    Resolution order for a model field: the model's own value, then the backend's
    (for ``reasoning_style``), then the ``defaults:`` block.
    """
    config_path = Path(path or os.getenv("AI4AIS_CONFIG") or DEFAULT_CONFIG_PATH)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text()) or {}
    defaults = raw.get("defaults", {}) or {}

    backends: dict[str, BackendConfig] = {}
    for name, spec in (raw.get("backends") or {}).items():
        backend_type = spec.get("type", "openai")
        if backend_type == "openai" and not spec.get("base_url"):
            raise ValueError(f"Backend {name!r} is type 'openai' but has no base_url")
        if not spec.get("api_key_env"):
            raise ValueError(f"Backend {name!r} is missing api_key_env")
        backends[name] = BackendConfig(
            name=name,
            type=backend_type,
            api_key_env=spec["api_key_env"],
            reasoning_style=spec.get("reasoning_style", "none"),
            base_url=spec.get("base_url"),
            max_tokens_param=spec.get("max_tokens_param", "max_tokens"),
            extra_headers=dict(spec.get("extra_headers") or {}),
        )

    default_timeout = float(defaults.get("timeout", 180))

    models: dict[str, ModelConfig] = {}
    for spec in raw.get("models") or []:
        model_id = spec.get("id")
        if not model_id:
            raise ValueError(f"Model entry missing 'id': {spec!r}")
        backend_name = spec.get("backend")
        if backend_name not in backends:
            raise ValueError(
                f"Model {model_id!r} references unknown backend {backend_name!r}. "
                f"Known backends: {sorted(backends)}"
            )
        backend = backends[backend_name]
        models[model_id] = ModelConfig(
            id=model_id,
            label=spec.get("label", model_id),
            backend=backend,
            model_name=spec.get("model_name", model_id),
            reasoning_effort=spec.get("reasoning_effort"),
            # A model may override the backend's reasoning style.
            reasoning_style=spec.get("reasoning_style", backend.reasoning_style),
            max_tokens=_coalesce(spec.get("max_tokens"), defaults.get("max_tokens")),
            temperature=_coalesce(spec.get("temperature"), defaults.get("temperature")),
            top_p=_coalesce(spec.get("top_p"), defaults.get("top_p")),
            thinking_budget_tokens=spec.get("thinking_budget_tokens"),
            openrouter_provider=spec.get("openrouter_provider"),
            timeout=float(spec.get("timeout", default_timeout)),
        )

    if not models:
        raise ValueError("Config defines no models")

    default_panel_models = list(raw.get("default_panel_models") or list(models)[:6])
    # Drop any ids that don't resolve to a real model so the UI never 404s.
    default_panel_models = [m for m in default_panel_models if m in models] or [
        next(iter(models))
    ]

    panel_count = int(defaults.get("panel_count", min(6, len(models))))
    panel_count = max(1, min(6, panel_count))

    reasoning_effort_options = list(
        defaults.get("reasoning_effort_options")
        or [DEFAULT_EFFORT, "none", "minimal", "low", "medium", "high"]
    )

    return AppConfig(
        models=models,
        backends=backends,
        default_panel_models=default_panel_models,
        panel_count=panel_count,
        reasoning_effort_options=reasoning_effort_options,
    )
