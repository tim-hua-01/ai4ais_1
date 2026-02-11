import httpx
import time
import json
from typing import Tuple, Optional, Dict
from anthropic import AsyncAnthropic


def extract_anthropic_content(content_blocks: list) -> Tuple[Optional[str], Optional[str]]:
    """Extract thinking and text from Anthropic response content blocks.

    Returns:
        Tuple of (thinking, content)
    """
    thinking = None
    content = None

    for block in content_blocks:
        try:
            if block.type == "thinking":
                thinking = block.thinking
            elif block.type == "text":
                content = block.text
        except AttributeError as e:
            # Log unexpected block structure
            import sys
            print(f"Warning: Unexpected Anthropic block structure: {e}", file=sys.stderr)

    return thinking, content


def format_response(
    content: str, thinking: Optional[str] = None, error: Optional[str] = None
) -> Dict:
    """Format API response with thinking and content separated.

    Args:
        content: The main response content
        thinking: Optional thinking/reasoning content
        error: Optional error message (takes precedence)

    Returns:
        Dict with 'thinking' and 'content' keys
    """
    if error:
        return {"content": error, "thinking": None}

    return {
        "content": content or "Error: No content in response",
        "thinking": thinking,
    }


async def call_openai_gpt5(messages: list, api_key: str) -> Tuple[Dict, float]:
    """Call OpenAI GPT-5.2 with reasoning_effort parameter."""
    start = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "gpt-5.2",
                    "messages": messages,
                    "reasoning_effort": "medium",
                    "max_completion_tokens": 16000,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

            # Validate response structure
            if not data.get("choices") or len(data["choices"]) == 0:
                raise ValueError("API returned empty choices array")
            if "message" not in data["choices"][0]:
                raise ValueError("API response missing message field")
            if "content" not in data["choices"][0]["message"]:
                raise ValueError("API response missing content field")

            content = data["choices"][0]["message"]["content"]
            if not content:
                raise ValueError("API returned empty content")

            duration = time.time() - start
            return format_response(content), duration
    except httpx.TimeoutException:
        duration = time.time() - start
        return format_response("", error="Error: Request timeout after 120 seconds"), duration
    except httpx.HTTPStatusError as e:
        duration = time.time() - start
        error_msg = f"Error: HTTP {e.response.status_code} - {e.response.text[:200]}"
        return format_response("", error=error_msg), duration
    except json.JSONDecodeError as e:
        duration = time.time() - start
        return format_response("", error="Error: Invalid JSON response from API"), duration
    except Exception as e:
        duration = time.time() - start
        error_msg = f"Error: {type(e).__name__}: {str(e)}"
        return format_response("", error=error_msg), duration


async def call_anthropic_opus_46(messages: list, api_key: str) -> Tuple[Dict, float]:
    """Call Anthropic Claude 4.6 Opus with extended thinking and adaptive effort."""
    start = time.time()
    try:
        if not api_key:
            raise ValueError("API key is empty")

        # Extract system message if present (Anthropic uses separate system parameter)
        system_message = None
        filtered_messages = messages
        if messages and messages[0].get("role") == "system":
            system_message = messages[0].get("content")
            filtered_messages = messages[1:]

        client = AsyncAnthropic(api_key=api_key)
        create_params = {
            "model": "claude-opus-4-6",
            "max_tokens": 16000,
            "messages": filtered_messages,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": "high"},
        }
        if system_message:
            create_params["system"] = system_message

        response = await client.messages.create(**create_params)

        if not response.content:
            raise ValueError("Anthropic API returned empty content")

        thinking, content = extract_anthropic_content(response.content)
        duration = time.time() - start
        return format_response(content, thinking=thinking), duration
    except TimeoutError:
        duration = time.time() - start
        return format_response("", error="Error: Request timeout"), duration
    except Exception as e:
        duration = time.time() - start
        error_type = type(e).__name__
        error_msg = f"Error: {error_type}: {str(e)[:100]}"
        return format_response("", error=error_msg), duration


async def call_anthropic_opus_45(messages: list, api_key: str) -> Tuple[Dict, float]:
    """Call Anthropic Claude 4.5 Opus with thinking_budget_tokens."""
    start = time.time()
    try:
        if not api_key:
            raise ValueError("API key is empty")

        # Extract system message if present (Anthropic uses separate system parameter)
        system_message = None
        filtered_messages = messages
        if messages and messages[0].get("role") == "system":
            system_message = messages[0].get("content")
            filtered_messages = messages[1:]

        client = AsyncAnthropic(api_key=api_key)
        create_params = {
            "model": "claude-opus-4-5-20251101",
            "max_tokens": 16000,
            "messages": filtered_messages,
            "thinking": {"type": "enabled", "budget_tokens": 5000},
        }
        if system_message:
            create_params["system"] = system_message

        response = await client.messages.create(**create_params)

        if not response.content:
            raise ValueError("Anthropic API returned empty content")

        thinking, content = extract_anthropic_content(response.content)
        duration = time.time() - start
        return format_response(content, thinking=thinking), duration
    except TimeoutError:
        duration = time.time() - start
        return format_response("", error="Error: Request timeout"), duration
    except Exception as e:
        duration = time.time() - start
        error_type = type(e).__name__
        error_msg = f"Error: {error_type}: {str(e)[:100]}"
        return format_response("", error=error_msg), duration


async def call_zai_glm47(messages: list, api_key: str) -> Tuple[Dict, float]:
    """Call Z.AI GLM-4.7 model."""
    start = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.z.ai/api/paas/v4/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept-Language": "en-US,en",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "glm-4.7",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 16000,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

            # Validate response structure
            if not data.get("choices") or len(data["choices"]) == 0:
                raise ValueError("API returned empty choices array")
            if "message" not in data["choices"][0]:
                raise ValueError("API response missing message field")

            message = data["choices"][0]["message"]
            reasoning = message.get("reasoning_content")
            content = message.get("content")

            if not content and not reasoning:
                raise ValueError("API returned no content or reasoning")

            duration = time.time() - start
            return format_response(content or "", thinking=reasoning), duration
    except httpx.TimeoutException:
        duration = time.time() - start
        return format_response("", error="Error: Request timeout after 120 seconds"), duration
    except httpx.HTTPStatusError as e:
        duration = time.time() - start
        error_msg = f"Error: HTTP {e.response.status_code} - {e.response.text[:200]}"
        return format_response("", error=error_msg), duration
    except json.JSONDecodeError:
        duration = time.time() - start
        return format_response("", error="Error: Invalid JSON response from API"), duration
    except Exception as e:
        duration = time.time() - start
        error_type = type(e).__name__
        error_msg = f"Error: {error_type}: {str(e)}"
        return format_response("", error=error_msg), duration


async def call_moonshot_kimi(messages: list, api_key: str) -> Tuple[Dict, float]:
    """Call Moonshot Kimi K2.5 model using OpenAI-compatible API."""
    start = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.moonshot.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "kimi-k2.5",
                    "messages": messages,
                    "temperature": 1.0,
                    "max_tokens": 16000,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

            # Validate response structure
            if not data.get("choices") or len(data["choices"]) == 0:
                raise ValueError("API returned empty choices array")
            if "message" not in data["choices"][0]:
                raise ValueError("API response missing message field")

            message = data["choices"][0]["message"]
            reasoning = message.get("reasoning_content")
            content = message.get("content")

            if not content and not reasoning:
                raise ValueError("API returned no content or reasoning")

            duration = time.time() - start
            return format_response(content or "", thinking=reasoning), duration
    except httpx.TimeoutException:
        duration = time.time() - start
        return format_response("", error="Error: Request timeout after 120 seconds"), duration
    except httpx.HTTPStatusError as e:
        duration = time.time() - start
        error_msg = f"Error: HTTP {e.response.status_code} - {e.response.text[:200]}"
        return format_response("", error=error_msg), duration
    except json.JSONDecodeError:
        duration = time.time() - start
        return format_response("", error="Error: Invalid JSON response from API"), duration
    except Exception as e:
        duration = time.time() - start
        error_type = type(e).__name__
        error_msg = f"Error: {error_type}: {str(e)}"
        return format_response("", error=error_msg), duration


async def call_openrouter_gemini(messages: list, api_key: str) -> Tuple[Dict, float]:
    """Call OpenRouter Gemini-3-pro-preview using OpenAI-compatible API."""
    start = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "AI4AIS Comparison Panel",
                },
                json={
                    "model": "google/gemini-3-pro-preview",
                    "messages": messages,
                    "temperature": 1.0,
                    "max_tokens": 16000,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

            # Validate response structure
            if not data.get("choices") or len(data["choices"]) == 0:
                raise ValueError("API returned empty choices array")
            if "message" not in data["choices"][0]:
                raise ValueError("API response missing message field")
            if "content" not in data["choices"][0]["message"]:
                raise ValueError("API response missing content field")

            content = data["choices"][0]["message"]["content"]
            if not content:
                raise ValueError("API returned empty content")

            duration = time.time() - start
            return format_response(content), duration
    except httpx.TimeoutException:
        duration = time.time() - start
        return format_response("", error="Error: Request timeout after 120 seconds"), duration
    except httpx.HTTPStatusError as e:
        duration = time.time() - start
        error_msg = f"Error: HTTP {e.response.status_code} - {e.response.text[:200]}"
        return format_response("", error=error_msg), duration
    except json.JSONDecodeError:
        duration = time.time() - start
        return format_response("", error="Error: Invalid JSON response from API"), duration
    except Exception as e:
        duration = time.time() - start
        error_type = type(e).__name__
        error_msg = f"Error: {error_type}: {str(e)}"
        return format_response("", error=error_msg), duration
