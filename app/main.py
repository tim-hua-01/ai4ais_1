from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import asyncio
import os
from dotenv import load_dotenv

from .api_clients import (
    call_openai_gpt5,
    call_anthropic_opus_46,
    call_anthropic_opus_45,
    call_zai_glm47,
    call_moonshot_kimi,
    call_openrouter_gemini,
)

load_dotenv()

app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Model registry mapping model IDs to API client functions
MODEL_REGISTRY = {
    "openai/gpt-5.2": (call_openai_gpt5, "OPENAI_API_KEY"),
    "anthropic/claude-4.6-opus": (call_anthropic_opus_46, "ANTHROPIC_API_KEY"),
    "anthropic/claude-4.5-opus": (call_anthropic_opus_45, "ANTHROPIC_API_KEY"),
    "zai/glm-4.7": (call_zai_glm47, "ZAI_API_KEY"),
    "moonshotai/kimi-k2.5": (call_moonshot_kimi, "MOONSHOT_API_KEY"),
    "openrouter/google/gemini-3-pro-preview": (
        call_openrouter_gemini,
        "OPENROUTER_API_KEY",
    ),
}


class Panel(BaseModel):
    model: str
    messages: list[dict]
    enabled: bool


class ChatRequest(BaseModel):
    panels: list[Panel]


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Handle multi-panel chat requests with parallel API calls."""
    # Validate request
    if not request.panels:
        return {"error": "No panels provided", "results": []}

    tasks = []
    panel_info = []

    for idx, panel in enumerate(request.panels):
        try:
            if panel.enabled:
                # Validate panel data
                if not panel.model:
                    panel_info.append(("error", "model_missing"))
                    tasks.append(asyncio.sleep(0))
                    continue

                if not isinstance(panel.messages, list) or len(panel.messages) == 0:
                    panel_info.append(("error", "messages_empty"))
                    tasks.append(asyncio.sleep(0))
                    continue

                model = panel.model

                if model not in MODEL_REGISTRY:
                    panel_info.append(("error", "model_unknown"))
                    tasks.append(asyncio.sleep(0))
                    continue

                api_func, env_var = MODEL_REGISTRY[model]
                api_key = os.getenv(env_var)

                if not api_key:
                    panel_info.append(("error", f"missing_key:{env_var}"))
                    tasks.append(asyncio.sleep(0))
                    continue

                if api_key.startswith("your_"):
                    panel_info.append(("error", f"unconfigured_key:{env_var}"))
                    tasks.append(asyncio.sleep(0))
                    continue

                # Create task for this panel
                tasks.append(api_func(panel.messages, api_key))
                panel_info.append(("call", model))
            else:
                tasks.append(asyncio.sleep(0))
                panel_info.append(("skip", None))
        except Exception as e:
            # Catch any unexpected errors in panel setup
            import sys
            print(f"Error setting up panel {idx}: {e}", file=sys.stderr)
            panel_info.append(("error", f"setup_error:{str(e)[:50]}"))
            tasks.append(asyncio.sleep(0))

    # Execute all API calls in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Format results
    formatted_results = []
    for i, result in enumerate(results):
        try:
            if i >= len(panel_info):
                formatted_results.append(
                    {"content": "Error: Internal server error - panel info missing", "duration": 0}
                )
                continue

            info_type, info_data = panel_info[i]

            if info_type == "skip":
                formatted_results.append(None)
            elif info_type == "error":
                error_msg = f"Error: "
                if info_data == "model_missing":
                    error_msg += "Model not selected"
                elif info_data == "messages_empty":
                    error_msg += "No messages to send"
                elif info_data == "model_unknown":
                    error_msg += "Unknown model"
                elif info_data.startswith("missing_key:"):
                    key_name = info_data.split(":", 1)[1]
                    error_msg += f"API key not configured ({key_name})"
                elif info_data.startswith("unconfigured_key:"):
                    key_name = info_data.split(":", 1)[1]
                    error_msg += f"API key not set ({key_name})"
                elif info_data.startswith("setup_error:"):
                    error_msg += f"Setup failed: {info_data.split(':', 1)[1]}"
                else:
                    error_msg += str(info_data)

                formatted_results.append({"content": error_msg, "thinking": None, "duration": 0})
            elif isinstance(result, Exception):
                formatted_results.append({
                    "content": f"Error: {type(result).__name__}: {str(result)}",
                    "thinking": None,
                    "duration": 0
                })
            elif isinstance(result, tuple) and len(result) == 2:
                response_data, duration = result
                # Handle dict response with thinking and content
                if isinstance(response_data, dict):
                    formatted_results.append({
                        "content": response_data.get("content", ""),
                        "thinking": response_data.get("thinking"),
                        "duration": round(float(duration), 2)
                    })
                elif isinstance(response_data, str):
                    # Legacy string response
                    formatted_results.append({
                        "content": response_data,
                        "thinking": None,
                        "duration": round(float(duration), 2)
                    })
                else:
                    formatted_results.append({
                        "content": str(response_data),
                        "thinking": None,
                        "duration": round(float(duration), 2)
                    })
            else:
                # Unexpected result format
                formatted_results.append({
                    "content": f"Error: Unexpected response format from API",
                    "thinking": None,
                    "duration": 0
                })
        except Exception as e:
            # Catch any errors during result formatting
            import sys
            print(f"Error formatting result {i}: {e}", file=sys.stderr)
            formatted_results.append({
                "content": f"Error: Failed to process response",
                "thinking": None,
                "duration": 0
            })

    return {"results": formatted_results}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
