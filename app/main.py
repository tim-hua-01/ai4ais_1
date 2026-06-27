"""FastAPI server for the multi-model comparison panel.

Models and providers are defined entirely in ``config/models.yaml`` (see
``app.config``). This module just loads that config, exposes it to the frontend
via ``/api/models`` / ``/api/config``, and dispatches chat requests to the
generic backend handlers in ``app.api_clients``.
"""

from __future__ import annotations

import asyncio
import os
import sys

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .api_clients import call_model
from .config import AppConfig, load_config

# API keys are read straight from the environment (os.getenv in app.config). Run
# Set OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY before starting.

# Resolve paths relative to the project root so the server runs from any CWD.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="AI4AIS Multi-Model Comparison Panel")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Loaded once at import. Edit config/models.yaml and restart (or use --reload).
CONFIG: AppConfig = load_config()


class Panel(BaseModel):
    model: str
    messages: list[dict]
    enabled: bool
    reasoning_effort: str | None = None  # per-panel override; None => model default


class ChatRequest(BaseModel):
    panels: list[Panel]


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/models")
async def list_models():
    """Model catalog for the frontend dropdowns and reasoning-effort selectors."""
    return {"models": CONFIG.model_summaries()}


@app.get("/api/config")
async def get_config():
    """UI defaults: which models populate panels on load, panel count, etc."""
    return {
        "default_panel_models": CONFIG.default_panel_models,
        "panel_count": CONFIG.panel_count,
        "reasoning_effort_options": CONFIG.reasoning_effort_options,
    }


async def _run_panel(panel: Panel) -> dict | None:
    """Execute one panel's request, returning a result dict (or None if skipped)."""
    if not panel.enabled:
        return None

    if not panel.model:
        return {"content": "Error: Model not selected", "thinking": None, "duration": 0}

    model = CONFIG.models.get(panel.model)
    if model is None:
        return {"content": f"Error: Unknown model '{panel.model}'", "thinking": None, "duration": 0}

    if not panel.messages:
        return {"content": "Error: No messages to send", "thinking": None, "duration": 0}

    api_key = model.backend.api_key
    if not api_key or api_key.startswith("your_"):
        return {
            "content": f"Error: API key not configured ({model.backend.api_key_env})",
            "thinking": None,
            "duration": 0,
        }

    effort = model.resolved_effort(panel.reasoning_effort)
    try:
        response_data, duration = await call_model(model, panel.messages, api_key, effort)
    except Exception as exc:  # noqa: BLE001 - never let one panel break the batch
        print(f"Error calling model {panel.model}: {exc}", file=sys.stderr)
        return {"content": f"Error: {type(exc).__name__}: {exc}", "thinking": None, "duration": 0}

    return {
        "content": response_data.get("content", ""),
        "thinking": response_data.get("thinking"),
        "duration": round(float(duration), 2),
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Run all enabled panels in parallel and return their results in order."""
    if not request.panels:
        return {"error": "No panels provided", "results": []}

    results = await asyncio.gather(
        *(_run_panel(panel) for panel in request.panels),
        return_exceptions=True,
    )

    formatted: list[dict | None] = []
    for result in results:
        if isinstance(result, BaseException):
            formatted.append(
                {"content": f"Error: {type(result).__name__}: {result}", "thinking": None, "duration": 0}
            )
        else:
            formatted.append(result)

    return {"results": formatted}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
