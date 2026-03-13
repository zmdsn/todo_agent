# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Test Commands

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_writer.py -v

# Run MCP server (stdio mode)
uv run todo-mcp

# Run OpenAI-compatible API server
uv run todo-agent serve --port 6501
```

## Architecture Overview

### Dual Service Mode
- **MCP Server** (`server.py:main`): STDIO-based MCP protocol server
- **OpenAI API** (`cli/main.py:serve`): HTTP server with `/v1/chat/completions` endpoint

Both use the same LangChain agent from `agent/` module.

### Core Modules

```
src/todo_mcp/
├── agent/          # LangChain agent, tools, prompts, session memory
├── api/            # OpenAI-compatible API layer
├── models/         # Task, Config (Pydantic models)
├── parser/         # MarkdownReader, MarkdownWriter
├── reminder/       # Notification and reminder system
├── utils/          # TimeParser, TaskEstimator
└── server.py       # MCP server implementation
```

### Task Storage
Tasks stored as Markdown files under `todo_root` (default: `~/todo/`):
```
todo/2026/Q1/03-March.md
```

### Task ID Format
```
{year}-{quarter}-{month}-{day}-{index}
Example: 2026-1-03-13-1  or  2026-Q1-03-13-1
```

### Date Header Formats
Supports two formats in markdown:
- `## 13日` - Chinese format
- `#### 3/13` - Slash format

### TASK_PATTERN Regex Groups
```python
TASK_PATTERN = r"^(\s*)(-|\*)\s+\[([ xX])\]\s+(.+)$"
# group(1) = indent
# group(2) = bullet (- or *)
# group(3) = status char (x or space)
# group(4) = content
```

### Task Counter Logic
When parsing tasks, the counter only resets when day **changes**, not on every header. This handles multiple sections for the same day.

## Key Configuration

Environment variables (from `.env`):
- `ANTHROPIC_BASE_URL` - LLM API endpoint
- `ANTHROPIC_MODEL` - Model name
- `ANTHROPIC_AUTH_TOKEN` - API key
- `TODO_API_KEY` - Server API key for protecting /v1/* endpoints (default: "happy")
