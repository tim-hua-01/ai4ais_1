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
uvicorn app.main:app --reload --port 8000
```
Then open `http://localhost:8000` in your browser.

## Multi-Model Comparison Panel Web Application

The project includes a FastAPI-based web application for comparing responses from multiple LLMs side-by-side.

### Architecture
- **Backend**: `app/main.py` - FastAPI server with async API endpoints
- **API Clients**: `app/api_clients.py` - Async HTTP clients for 6 different LLM providers
- **Frontend**: `templates/index.html`, `static/style.css`, `static/script.js` - Interactive panel UI
- **Configuration**: `.env` file for API keys

### Supported Models
1. **OpenAI GPT-5.2** - `reasoning_effort: "medium"`
2. **Anthropic Claude 4.6 Opus** - Extended thinking with adaptive effort (`"high"`)
3. **Anthropic Claude 4.5 Opus** - Extended thinking with `thinking_budget_tokens: 1500`
4. **Z.AI GLM-4.7** - Standard chat completion
5. **Moonshot Kimi K2.5** - OpenAI-compatible API
6. **OpenRouter Gemini-3-pro-preview** - OpenAI-compatible API

### Features
- Up to 6 panels, each with a selectable model dropdown
- Global message input to send to all models simultaneously
- Per-panel message input for model-specific queries
- Response timing display (in seconds) for latency comparison
- Multi-turn conversation support with history per panel
- Async parallel API calls for fast response aggregation

### Setup
Configure API keys in `.env` before running:
```
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
ZAI_API_KEY=your_key
MOONSHOT_API_KEY=your_key
OPENROUTER_API_KEY=your_key
```

### Implementation Notes
- All API calls use `httpx.AsyncClient` for async HTTP requests
- Requests executed in parallel via `asyncio.gather` for efficiency
- Timing measured server-side for accuracy
- Error handling returns error messages displayed in panels
- Frontend maintains conversation history client-side per panel
- Each API client function returns `(response_content, duration_in_seconds)` tuple

## Key Framework: inspect-ai

This project uses the `inspect-ai` framework for AI inspection/evaluation tasks. When working with this codebase:
- Refer to inspect-ai documentation for evaluation setup and task definitions
- Tasks typically involve creating inspection workflows and running evaluations
- Results may involve data analysis with pandas and visualization with matplotlib
