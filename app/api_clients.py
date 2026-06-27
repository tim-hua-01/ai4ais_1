"""Generic, config-driven API clients.

Two handlers cover every provider:

* :func:`call_openai_compatible` — any ``/chat/completions`` endpoint (OpenAI,
  OpenRouter, and anything else OpenAI-compatible), via ``httpx``.
* :func:`call_anthropic` — Anthropic Messages via the official SDK.

Both take a :class:`~app.config.ModelConfig` plus the conversation and an optional
per-request ``effort`` override, and return ``(response_dict, duration_seconds)``
where ``response_dict`` has ``content`` and ``thinking`` keys. :func:`call_model`
dispatches to the right one based on the backend type.

Reasoning effort is encoded per the model's ``reasoning_style`` (see
``config/models.yaml``), building per-backend sampling params from the model config.
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional, Tuple

import httpx

from .config import ModelConfig

def format_response(
    content: Optional[str], thinking: Optional[str] = None, error: Optional[str] = None
) -> dict:
    """Shape every handler returns: ``{"content": ..., "thinking": ...}``."""
    if error:
        return {"content": error, "thinking": None}
    return {"content": content or "Error: No content in response", "thinking": thinking}


def _effort_is_active(effort: Optional[str]) -> bool:
    return effort is not None and effort.strip().lower() not in {"", "none", "default"}


# --- OpenAI-compatible backends ------------------------------------------------


def _build_openai_payload(
    model: ModelConfig, messages: list, effort: Optional[str]
) -> dict[str, Any]:
    """Assemble the request body for an OpenAI-compatible chat completion."""
    backend = model.backend
    payload: dict[str, Any] = {
        "model": model.model_name,
        "messages": messages,
    }
    if model.max_tokens is not None:
        payload[backend.max_tokens_param] = model.max_tokens
    if model.temperature is not None:
        payload["temperature"] = model.temperature
    if model.top_p is not None:
        payload["top_p"] = model.top_p

    # Reasoning effort, encoded per the resolved style.
    if _effort_is_active(effort):
        if model.reasoning_style == "effort":
            payload["reasoning_effort"] = effort
        elif model.reasoning_style == "openrouter":
            payload["reasoning"] = {"effort": effort}
        # styles "none"/anthropic-only => nothing sent here

    # OpenRouter provider routing, e.g. "atlas-cloud/fp8".
    if model.openrouter_provider:
        slug, _, quant = model.openrouter_provider.partition("/")
        provider_routing: dict[str, Any] = {"order": [slug], "allow_fallbacks": False}
        if quant:
            provider_routing["quantizations"] = [quant]
        payload["provider"] = provider_routing

    return payload


def _extract_openai_message(data: dict) -> Tuple[str, Optional[str]]:
    """Pull (content, thinking) out of an OpenAI-compatible response."""
    if not data.get("choices"):
        raise ValueError("API returned empty choices array")
    message = data["choices"][0].get("message")
    if not isinstance(message, dict):
        raise ValueError("API response missing message field")
    content = message.get("content") or ""
    # Different providers expose reasoning under different keys.
    thinking = (
        message.get("reasoning_content")
        or message.get("reasoning")
        or None
    )
    if not content and not thinking:
        raise ValueError("API returned no content or reasoning")
    return content, thinking


async def call_openai_compatible(
    model: ModelConfig,
    messages: list,
    api_key: str,
    effort: Optional[str] = None,
) -> Tuple[dict, float]:
    """Call any OpenAI-compatible ``/chat/completions`` endpoint."""
    start = time.time()
    backend = model.backend
    if not backend.base_url:
        raise ValueError(f"Backend {backend.name!r} has no base_url for OpenAI-compatible calls")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **backend.extra_headers,
    }
    url = f"{backend.base_url.rstrip('/')}/chat/completions"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=_build_openai_payload(model, messages, effort),
                timeout=model.timeout,
            )
            response.raise_for_status()
            content, thinking = _extract_openai_message(response.json())
            return format_response(content, thinking=thinking), time.time() - start
    except httpx.TimeoutException:
        return (
            format_response("", error=f"Error: Request timeout after {model.timeout:g}s"),
            time.time() - start,
        )
    except httpx.HTTPStatusError as exc:
        error_msg = f"Error: HTTP {exc.response.status_code} - {exc.response.text[:300]}"
        return format_response("", error=error_msg), time.time() - start
    except json.JSONDecodeError:
        return format_response("", error="Error: Invalid JSON response from API"), time.time() - start
    except Exception as exc:  # noqa: BLE001 - surface any failure to the panel
        return (
            format_response("", error=f"Error: {type(exc).__name__}: {exc}"),
            time.time() - start,
        )


# --- Anthropic backend ---------------------------------------------------------


def _extract_anthropic_content(content_blocks: list) -> Tuple[Optional[str], Optional[str]]:
    """Return (thinking, content) from Anthropic response content blocks."""
    thinking: Optional[str] = None
    content: Optional[str] = None
    for block in content_blocks:
        block_type = getattr(block, "type", None)
        if block_type == "thinking":
            thinking = getattr(block, "thinking", None)
        elif block_type == "text":
            content = getattr(block, "text", None)
    return thinking, content


def _build_anthropic_kwargs(
    model: ModelConfig, messages: list, effort: Optional[str]
) -> dict[str, Any]:
    """Assemble create() kwargs, splitting out the system message and reasoning.

    ``adaptive`` style => adaptive thinking + ``output_config.effort`` (current
    Opus models). ``budget`` style => manual extended thinking via
    ``thinking_budget_tokens`` (older models). Otherwise no thinking.
    """
    system_message: Optional[str] = None
    convo = messages
    if messages and messages[0].get("role") == "system":
        system_message = messages[0].get("content")
        convo = messages[1:]

    kwargs: dict[str, Any] = {
        "model": model.model_name,
        "max_tokens": model.max_tokens or 16000,
        "messages": convo,
    }
    if model.temperature is not None:
        kwargs["temperature"] = model.temperature
    if system_message:
        kwargs["system"] = system_message

    if model.reasoning_style == "budget" and model.thinking_budget_tokens:
        budget = model.thinking_budget_tokens
        if budget >= kwargs["max_tokens"]:
            kwargs["max_tokens"] = budget + 4096
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
    elif model.reasoning_style == "adaptive" and _effort_is_active(effort):
        kwargs["thinking"] = {"type": "adaptive"}
        kwargs["output_config"] = {"effort": effort}

    return kwargs


async def call_anthropic(
    model: ModelConfig,
    messages: list,
    api_key: str,
    effort: Optional[str] = None,
) -> Tuple[dict, float]:
    """Call the Anthropic Messages API via the official async SDK."""
    from anthropic import AsyncAnthropic

    start = time.time()
    try:
        client = AsyncAnthropic(api_key=api_key, timeout=model.timeout)
        response = await client.messages.create(
            **_build_anthropic_kwargs(model, messages, effort)
        )
        if not response.content:
            raise ValueError("Anthropic API returned empty content")
        thinking, content = _extract_anthropic_content(response.content)
        return format_response(content, thinking=thinking), time.time() - start
    except Exception as exc:  # noqa: BLE001 - surface any failure to the panel
        return (
            format_response("", error=f"Error: {type(exc).__name__}: {str(exc)[:300]}"),
            time.time() - start,
        )


# --- Dispatch ------------------------------------------------------------------


async def call_model(
    model: ModelConfig,
    messages: list,
    api_key: str,
    effort: Optional[str] = None,
) -> Tuple[dict, float]:
    """Route to the correct backend handler based on ``model.backend.type``."""
    if model.backend.type == "anthropic":
        return await call_anthropic(model, messages, api_key, effort)
    return await call_openai_compatible(model, messages, api_key, effort)
