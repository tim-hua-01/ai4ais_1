# AI4AIS Multi-Model Comparison Panel

A local web application for comparing responses from multiple Large Language Models (LLMs) side-by-side. Send the same prompt to up to 6 different models simultaneously and compare their responses, timing, and reasoning processes.

## Features

- **Multi-Model Comparison**: Compare up to 6 different LLM models side-by-side
- **Real-Time Responses**: Models respond independently with individual response timing
- **Extended Thinking Display**: View reasoning/thinking blocks in collapsible dropdowns
- **Markdown Rendering**: All responses render markdown for better readability
- **Editable Panel Labels**: Customize each panel's title with notes about configuration
- **Per-Panel Controls**: Send messages to individual models or all models at once
- **Resizable Panels**: Adjust chat area height by dragging the divider between chat and input
- **Response Timing**: See how long each model takes to respond
- **Per-Model History**: Each panel maintains independent conversation history

## Supported Models

1. **OpenAI GPT-5.2** - `openai/gpt-5.2`
   - Uses `reasoning_effort: "medium"` for structured reasoning

2. **Anthropic Claude 4.6 Opus** - `anthropic/claude-4.6-opus`
   - Extended thinking with adaptive effort (`effort: "high"`)

3. **Anthropic Claude 4.5 Opus** - `anthropic/claude-4.5-opus`
   - Extended thinking with 5000 token budget

4. **Z.AI GLM-4.7** - `zai/glm-4.7`
   - Standard chat completion with reasoning support

5. **Moonshot Kimi K2.5** - `moonshotai/kimi-k2.5`
   - OpenAI-compatible API with reasoning capabilities

6. **OpenRouter Gemini-3-pro-preview** - `openrouter/google/gemini-3-pro-preview`
   - OpenAI-compatible API via OpenRouter

## Setup

### Prerequisites

- Python 3.11+
- `uv` package manager (or `pip`)
- API keys for the models you want to use

### Installation

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Create `.env` file** with your API keys:
   ```
   OPENAI_API_KEY=your_openai_key
   ANTHROPIC_API_KEY=your_anthropic_key
   ZAI_API_KEY=your_zai_key
   MOONSHOT_API_KEY=your_moonshot_key
   OPENROUTER_API_KEY=your_openrouter_key
   ```

3. **Run the server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

4. **Open in browser**:
   ```
   http://localhost:8000
   ```

## Usage

### Main Interface

- **Panel Count Selector**: Choose 1-6 panels in the header dropdown
- **Panel Titles**: Click any panel title to edit and add custom notes
- **Model Selector**: Narrow dropdown to change which model runs in each panel

### Sending Messages

#### Send to All Models
- Type your message in the main input area (bottom of screen)
- Click **"Send to All"** button (right side) OR
- Press **Cmd+Enter** (macOS) / **Ctrl+Enter** (Windows)
- Press **Shift+Enter** to add a newline in your message
- The message appears in all panels and sends to all selected models in parallel

#### Send to Single Model
- Type in the input field at the bottom of a specific panel
- Click **"Send"** button for that panel OR
- Press **Enter** to send
- Press **Shift+Enter** to add a newline in your message
- The message only appears in that panel's conversation
- You can send to individual panels while waiting for other models to respond

### Panel Controls

- **Reset**: Clear a single panel's conversation history without affecting others
- **Model Selector**: Change which model is used in a panel (narrow dropdown in panel header)
- **Editable Title**: Click the panel title to rename it with configuration notes
- **Main Resize Divider**: Drag the divider between panels and input section to adjust space allocation

### Response Features

- **Thinking/Reasoning Blocks**: Click "Thinking (click to expand)" to view extended thinking
  - GPT-5.2 shows reasoning steps
  - Claude 4.6/4.5 show extended thinking content
  - Other models show reasoning content if available

- **Markdown Support**: Responses render:
  - Bold, italic, code formatting
  - Links
  - Lists and blockquotes
  - Code blocks with syntax highlighting

- **Response Timing**: Gray text below responses shows how long the model took to respond (in seconds)

## Architecture

### Backend
- **Framework**: FastAPI (async Python web framework)
- **API Clients**: Async HTTP clients for each model provider
  - Uses official Anthropic SDK for Claude models
  - Uses `httpx.AsyncClient` for other providers
- **Concurrency**: All model requests run in parallel using `asyncio.gather()`

### Frontend
- **HTML/CSS/JavaScript**: Vanilla implementation (no framework)
- **Markdown Rendering**: `marked.js` library for markdown-to-HTML conversion
- **Styling**: Clean, responsive CSS with beige/tan color scheme

### File Structure
```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI server and request routing
│   └── api_clients.py       # API client implementations for 6 models
├── static/
│   ├── script.js            # Frontend interaction logic
│   └── style.css            # Styling and layout
├── templates/
│   └── index.html           # Main HTML page
├── .env                     # API keys (create this)
├── pyproject.toml           # Project dependencies
└── README.md               # This file
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Cmd+Enter** (macOS) / **Ctrl+Enter** (Windows) | Send message to all models |
| **Enter** (in panel input) | Send to that panel's model |
| **Shift+Enter** (any input) | Add a newline to your message |

## Color Scheme

- **User Messages**: Warm tan beige (#dcc6b8)
- **Model Responses**: Lighter beige (#ede5db)
- **Text**: Black on both for high contrast
- **Panel Borders**: Dark gray for clear visual separation
- **Links**: Black with underline on hover

## Troubleshooting

### Model returns "Error: API key not configured"
- Verify your `.env` file has the correct environment variables
- Check that API keys are not placeholders like `your_key`

### No response from a model
- Check API key is valid for that provider
- Check rate limits haven't been exceeded
- Look at browser console (F12) for error messages
- Check server logs for detailed error information

### Responses are slow or timing out
- Some models have higher latency
- Check your internet connection
- Consider trying with fewer panels initially

## Performance Notes

- All model requests run in parallel - waiting time = slowest model, not sum of all
- Response timing is measured server-side for accuracy
- Chat history stored in browser memory (clears on page refresh)
- Markdown rendering happens in the browser after receiving response

## Development

To modify the code:

1. **API Clients**: Edit `app/api_clients.py` to change model parameters or add new models
2. **Server Logic**: Edit `app/main.py` to change request handling
3. **Frontend Logic**: Edit `static/script.js` for UI interactions
4. **Styling**: Edit `static/style.css` for visual changes
5. **HTML Structure**: Edit `templates/index.html` for layout changes

All files hot-reload when running with `--reload` flag.

## Limitations

- Conversations are not persisted (lost on page refresh)
- No authentication/user management
- Maximum token limits depend on each model's API
- Some models may have usage rate limits

## Future Enhancements

Possible improvements:
- Save/export conversations
- Add more models
- Streaming responses
- User authentication
- Conversation history persistence
- Custom system prompts per panel
