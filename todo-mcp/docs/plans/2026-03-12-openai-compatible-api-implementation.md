# OpenAI Compatible API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add OpenAI-compatible `/v1/chat/completions` endpoint to Todo Agent API, enabling direct use with OpenAI SDK.

**Architecture:** Create an OpenAI compatibility layer as a FastAPI router that converts OpenAI format requests to internal Agent calls, then converts responses back to OpenAI format.

**Tech Stack:** FastAPI, Pydantic, existing LangChain Agent

---

## Task 1: OpenAI Data Models

**Files:**
- Create: `src/todo_mcp/api/openai_compat.py`
- Create: `tests/test_openai_compat.py`

**Step 1: Write the failing test**

```python
# tests/test_openai_compat.py
import pytest
from todo_mcp.api.openai_compat import (
    ChatMessage,
    OpenAIChatRequest,
    OpenAIChatResponse,
    Choice,
    Usage,
)


def test_chat_message_creation():
    """Test ChatMessage model creation."""
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"


def test_chat_message_with_name():
    """Test ChatMessage with optional name field."""
    msg = ChatMessage(role="user", content="Hello", name="session-123")
    assert msg.name == "session-123"


def test_openai_chat_request():
    """Test OpenAIChatRequest model."""
    request = OpenAIChatRequest(
        model="todo-agent",
        messages=[
            ChatMessage(role="user", content="今天有什么任务？")
        ]
    )
    assert request.model == "todo-agent"
    assert len(request.messages) == 1
    assert request.temperature is None


def test_openai_chat_response():
    """Test OpenAIChatResponse model."""
    response = OpenAIChatResponse(
        id="chatcmpl-test123",
        created=1710123456,
        model="todo-agent",
        choices=[
            Choice(
                index=0,
                message=ChatMessage(role="assistant", content="响应内容"),
                finish_reason="stop"
            )
        ]
    )
    assert response.id == "chatcmpl-test123"
    assert response.object == "chat.completion"
    assert len(response.choices) == 1


def test_usage_defaults():
    """Test Usage model defaults."""
    usage = Usage()
    assert usage.prompt_tokens == 0
    assert usage.completion_tokens == 0
    assert usage.total_tokens == 0
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_openai_compat.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# src/todo_mcp/api/openai_compat.py
"""OpenAI API 兼容层。"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class ChatMessage(BaseModel):
    """聊天消息。"""
    role: Literal["system", "user", "assistant"]
    content: str
    name: Optional[str] = None


class OpenAIChatRequest(BaseModel):
    """OpenAI 聊天请求。"""
    model: str = "todo-agent"
    messages: list[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    user: Optional[str] = None


class Usage(BaseModel):
    """Token 使用统计。"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class Choice(BaseModel):
    """选择项。"""
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class OpenAIChatResponse(BaseModel):
    """OpenAI 聊天响应。"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage = Field(default_factory=Usage)


class ModelInfo(BaseModel):
    """模型信息。"""
    id: str
    object: str = "model"
    created: int
    owned_by: str = "local"


class ModelList(BaseModel):
    """模型列表。"""
    object: str = "list"
    data: list[ModelInfo]
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_openai_compat.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/api/openai_compat.py tests/test_openai_compat.py
git commit -m "feat(api): add OpenAI compatible data models"
```

---

## Task 2: Message Conversion

**Files:**
- Modify: `src/todo_mcp/api/openai_compat.py`
- Modify: `tests/test_openai_compat.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_openai_compat.py

def test_convert_openai_messages_single():
    """Test converting single user message."""
    from todo_mcp.api.openai_compat import convert_openai_messages

    messages = [ChatMessage(role="user", content="Hello")]
    session_id, user_message = convert_openai_messages(messages)

    assert user_message == "Hello"
    assert session_id == "default"


def test_convert_openai_messages_with_system():
    """Test converting messages with system prompt (should be ignored)."""
    from todo_mcp.api.openai_compat import convert_openai_messages

    messages = [
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="Hello"),
    ]
    session_id, user_message = convert_openai_messages(messages)

    assert user_message == "Hello"


def test_convert_openai_messages_conversation():
    """Test converting multi-turn conversation."""
    from todo_mcp.api.openai_compat import convert_openai_messages

    messages = [
        ChatMessage(role="user", content="First message"),
        ChatMessage(role="assistant", content="First response"),
        ChatMessage(role="user", content="Second message"),
    ]
    session_id, user_message = convert_openai_messages(messages)

    # Should extract the last user message
    assert user_message == "Second message"


def test_convert_openai_messages_empty():
    """Test converting empty message list."""
    from todo_mcp.api.openai_compat import convert_openai_messages

    session_id, user_message = convert_openai_messages([])

    assert user_message == ""
    assert session_id == "default"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_openai_compat.py::test_convert -v`
Expected: FAIL with ImportError

**Step 3: Write minimal implementation**

```python
# Add to src/todo_mcp/api/openai_compat.py

def convert_openai_messages(messages: list[ChatMessage]) -> tuple[str, str]:
    """将 OpenAI 消息格式转换为 Agent 输入。

    Args:
        messages: OpenAI 格式的消息列表

    Returns:
        (session_id, user_message)
    """
    session_id = "default"
    user_message = ""

    # 最后一条 user 消息作为输入
    for msg in reversed(messages):
        if msg.role == "user":
            user_message = msg.content
            break

    return session_id, user_message
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_openai_compat.py::test_convert -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/api/openai_compat.py tests/test_openai_compat.py
git commit -m "feat(api): add OpenAI message conversion"
```

---

## Task 3: FastAPI Router

**Files:**
- Modify: `src/todo_mcp/api/openai_compat.py`
- Modify: `tests/test_openai_compat.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_openai_compat.py
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with OpenAI router."""
    from fastapi import FastAPI
    from todo_mcp.api.openai_compat import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestModelsEndpoint:
    """Test /v1/models endpoints."""

    def test_list_models(self, client):
        """Test listing models."""
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) >= 1
        assert any(m["id"] == "todo-agent" for m in data["data"])

    def test_get_model(self, client):
        """Test getting specific model."""
        response = client.get("/v1/models/todo-agent")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "todo-agent"
        assert data["object"] == "model"

    def test_get_model_not_found(self, client):
        """Test getting non-existent model."""
        response = client.get("/v1/models/nonexistent")
        assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_openai_compat.py::TestModelsEndpoint -v`
Expected: FAIL (router not defined)

**Step 3: Write minimal implementation**

```python
# Add to src/todo_mcp/api/openai_compat.py

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])


@router.get("/models")
async def list_models() -> dict:
    """列出可用模型。"""
    return {
        "object": "list",
        "data": [
            {
                "id": "todo-agent",
                "object": "model",
                "created": 1700000000,
                "owned_by": "local"
            }
        ]
    }


@router.get("/models/{model_id}")
async def get_model(model_id: str) -> dict:
    """获取模型信息。"""
    if model_id != "todo-agent":
        raise HTTPException(status_code=404, detail="Model not found")

    return {
        "id": "todo-agent",
        "object": "model",
        "created": 1700000000,
        "owned_by": "local"
    }
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_openai_compat.py::TestModelsEndpoint -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/api/openai_compat.py tests/test_openai_compat.py
git commit -m "feat(api): add OpenAI models endpoint"
```

---

## Task 4: Chat Completions Endpoint

**Files:**
- Modify: `src/todo_mcp/api/openai_compat.py`
- Modify: `tests/test_openai_compat.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_openai_compat.py
from unittest.mock import patch, MagicMock


class TestChatCompletions:
    """Test /v1/chat/completions endpoint."""

    def test_chat_completions_request_format(self, client):
        """Test chat completions accepts OpenAI format."""
        with patch("todo_mcp.api.openai_compat.get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_get_agent.return_value = mock_agent

            with patch("todo_mcp.api.openai_compat.run_agent") as mock_run:
                mock_run.return_value = "测试响应"

                response = client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "todo-agent",
                        "messages": [
                            {"role": "user", "content": "今天有什么任务？"}
                        ]
                    }
                )

        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "chat.completion"
        assert data["model"] == "todo-agent"
        assert len(data["choices"]) == 1
        assert data["choices"][0]["message"]["role"] == "assistant"
        assert "content" in data["choices"][0]["message"]

    def test_chat_completions_response_structure(self, client):
        """Test response has all required OpenAI fields."""
        import time

        with patch("todo_mcp.api.openai_compat.get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_get_agent.return_value = mock_agent

            with patch("todo_mcp.api.openai_compat.run_agent") as mock_run:
                mock_run.return_value = "响应内容"

                response = client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "todo-agent",
                        "messages": [
                            {"role": "user", "content": "测试"}
                        ]
                    }
                )

        data = response.json()
        assert "id" in data
        assert data["id"].startswith("chatcmpl-")
        assert "created" in data
        assert isinstance(data["created"], int)
        assert "usage" in data
        assert "choices" in data

    def test_chat_completions_with_user_field(self, client):
        """Test user field maps to session_id."""
        with patch("todo_mcp.api.openai_compat.get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_get_agent.return_value = mock_agent

            with patch("todo_mcp.api.openai_compat.run_agent") as mock_run:
                mock_run.return_value = "响应"

                response = client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "todo-agent",
                        "messages": [
                            {"role": "user", "content": "测试"}
                        ],
                        "user": "custom-session"
                    }
                )

        assert response.status_code == 200
        # Verify run_agent was called with custom session
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][2].session_id == "custom-session" or "custom-session" in str(call_args)
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_openai_compat.py::TestChatCompletions -v`
Expected: FAIL (endpoint not implemented)

**Step 3: Write minimal implementation**

```python
# Add to src/todo_mcp/api/openai_compat.py

import time
import uuid
from fastapi import Depends

# Import from existing server
from todo_mcp.agent import create_todo_agent, run_agent, session_manager


# Global agent instance
_agent = None


def get_agent():
    """获取或创建 agent 实例。"""
    global _agent
    if _agent is None:
        _agent = create_todo_agent()
    return _agent


@router.post("/chat/completions", response_model=OpenAIChatResponse)
async def chat_completions(request: OpenAIChatRequest) -> OpenAIChatResponse:
    """OpenAI 兼容的聊天补全端点。"""
    # 转换消息
    session_id, user_message = convert_openai_messages(request.messages)

    # 使用请求中的 user 字段作为 session_id
    if request.user:
        session_id = request.user

    # 调用现有 Agent
    agent = get_agent()
    response_text = run_agent(agent, user_message, session_manager, session_id)

    # 构建 OpenAI 格式响应
    return OpenAIChatResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
        object="chat.completion",
        created=int(time.time()),
        model=request.model,
        choices=[
            Choice(
                index=0,
                message=ChatMessage(role="assistant", content=response_text),
                finish_reason="stop"
            )
        ],
        usage=Usage()
    )
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_openai_compat.py::TestChatCompletions -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/api/openai_compat.py tests/test_openai_compat.py
git commit -m "feat(api): add OpenAI chat completions endpoint"
```

---

## Task 5: Integrate with Existing Server

**Files:**
- Modify: `src/todo_mcp/api/server.py`
- Modify: `tests/test_openai_compat.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_openai_compat.py

class TestServerIntegration:
    """Test OpenAI endpoints integrated with main server."""

    @pytest.fixture
    def server_client(self):
        """Create test client from main server."""
        from todo_mcp.api.server import create_app
        app = create_app()
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_openai_routes_included(self, server_client):
        """Test OpenAI routes are included in main server."""
        response = server_client.get("/v1/models")
        assert response.status_code == 200

    def test_openai_chat_on_main_server(self, server_client):
        """Test chat completions on main server."""
        with patch("todo_mcp.api.server.get_agent") as mock_get:
            mock_agent = MagicMock()
            mock_get.return_value = mock_agent

            with patch("todo_mcp.api.server.run_agent") as mock_run:
                mock_run.return_value = "集成测试响应"

                response = server_client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "todo-agent",
                        "messages": [{"role": "user", "content": "测试"}]
                    }
                )

        assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_openai_compat.py::TestServerIntegration -v`
Expected: FAIL (router not included)

**Step 3: Write minimal implementation**

```python
# Modify src/todo_mcp/api/server.py
# Add at the top with other imports:
from todo_mcp.api.openai_compat import router as openai_router

# In create_app(), add after middleware setup:
    app.include_router(openai_router)
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_openai_compat.py::TestServerIntegration -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/api/server.py tests/test_openai_compat.py
git commit -m "feat(api): integrate OpenAI router with main server"
```

---

## Task 6: Update Documentation

**Files:**
- Modify: `README.md`

**Step 1: Add documentation section**

Add to README.md after the HTTP 传输模式 section:

```markdown
### OpenAI 兼容 API

todo-mcp 提供完全兼容 OpenAI 格式的 API 端点，可以直接使用 OpenAI SDK 调用。

#### 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/chat/completions` | POST | 聊天补全 |
| `/v1/models` | GET | 列出可用模型 |
| `/v1/models/{model_id}` | GET | 获取模型信息 |

#### 使用 OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"  # 不需要真实 key
)

response = client.chat.completions.create(
    model="todo-agent",
    messages=[
        {"role": "user", "content": "今天有什么任务？"}
    ]
)

print(response.choices[0].message.content)
```

#### 使用 curl

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "todo-agent",
    "messages": [{"role": "user", "content": "添加任务：完成报告"}]
  }'
```

#### 会话管理

通过 `user` 参数指定会话 ID：

```python
response = client.chat.completions.create(
    model="todo-agent",
    messages=[{"role": "user", "content": "继续刚才的对话"}],
    user="my-session-id"  # 用于会话隔离
)
```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add OpenAI compatible API documentation"
```

---

## Task 7: Run Full Test Suite

**Step 1: Run all tests**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest -v`

Expected: All tests PASS

**Step 2: Fix any failures**

If any tests fail, debug and fix before proceeding.

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(api): complete OpenAI compatible API implementation"
```

---

## Summary

| Task | Component | Files |
|------|-----------|-------|
| 1 | Data Models | `api/openai_compat.py` |
| 2 | Message Conversion | `api/openai_compat.py` |
| 3 | Models Endpoint | `api/openai_compat.py` |
| 4 | Chat Completions | `api/openai_compat.py` |
| 5 | Server Integration | `api/server.py` |
| 6 | Documentation | `README.md` |
| 7 | Final Testing | - |
