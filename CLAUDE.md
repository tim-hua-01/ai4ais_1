# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ai4ais-1** is a Jupyter-based project using the `inspect-ai` framework. The primary technology stack includes:
- Python 3.11
- `inspect-ai` (>=0.3.174) - AI inspection/evaluation framework
- Jupyter environment (ipykernel, ipython, ipywidgets)
- Data science tools (pandas, matplotlib, statsmodels)
- Utility: python-dotenv for environment management, tqdm for progress bars

## Development Setup

### Environment Management
- **Python Version:** 3.11 (defined in `.python-version`)
- **Package Manager:** `uv` (modern Python package manager)
- **Virtual Environment:** `.venv` directory in project root

### Common Commands

#### Install dependencies
```bash
uv sync
```

#### Run Jupyter notebooks
```bash
jupyter notebook
```

#### Run Python scripts
```bash
python <script_name>.py
```

#### Run the multi-model comparison web app
```bash
uv run uvicorn app.main:app --reload --port 8000
```
Then open `http://localhost:8000` in your browser.

## Multi-Model Comparison Panel Web Application

The project includes a FastAPI-based web application for comparing responses from multiple LLMs side-by-side. It is **config-driven**: models and providers are defined in `config/models.yaml`, not in code.

### Architecture
- **Config**: `config/models.yaml` - single source of truth for models, backends, and UI defaults.
- **Config loader**: `app/config.py` - parses the YAML into typed dataclasses (`ModelConfig`, `BackendConfig`, `AppConfig`).
- **API Clients**: `app/api_clients.py` - two generic handlers, `call_openai_compatible` (httpx) and `call_anthropic` (SDK), with `call_model()` dispatching by backend type.
- **Backend**: `app/main.py` - FastAPI server. Endpoints: `/api/models`, `/api/config`, `/api/chat`.
- **Frontend**: `templates/index.html`, `static/style.css`, `static/script.js` - loads the model catalog from `/api/models` at runtime; nothing about models is hardcoded.

### Bundled models
chat-latest, gpt-5.2 (OpenAI); claude-opus-4.6, claude-opus-4.5 (Anthropic); glm-5.2, kimi-k2.5, gemini-3.1-pro, gemini-3.5-flash (all via OpenRouter). See `config/models.yaml`.

### Reasoning effort
Each model has a default `reasoning_effort`; the UI dropdown overrides it per panel. The wire encoding is set by the backend/model `reasoning_style`: `effort` (OpenAI), `openrouter` (`reasoning: {effort}`), `adaptive` (Anthropic adaptive + `output_config.effort`), `budget` (Anthropic `thinking_budget_tokens`), or `none`.

### Setup
API keys are read from the **environment** (no `.env`/dotenv) — set the relevant vars before starting the server. Relevant vars: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY` (GLM/Kimi/Gemini all route through OpenRouter). Override the config path with `AI4AIS_CONFIG`.

### Implementation Notes
- OpenAI-compatible calls use `httpx.AsyncClient`; Anthropic uses the official async SDK.
- Requests executed in parallel via `asyncio.gather`; timing measured server-side.
- Each handler returns `(response_dict, duration_seconds)` where the dict has `content` and `thinking` keys.
- Errors are returned as `Error: ...` content strings and shown in the panel, never raised to the client.
- `test_models.py` is a config-driven smoke test (`python test_models.py [model_id ...]`).

## Key Framework: inspect-ai

This project uses the `inspect-ai` framework for AI inspection/evaluation tasks. When working with this codebase:
- Refer to inspect-ai documentation for evaluation setup and task definitions
- Tasks typically involve creating inspection workflows and running evaluations
- Results may involve data analysis with pandas and visualization with matplotlib
