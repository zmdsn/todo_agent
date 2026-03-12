"""Tests for OpenAI compatible data models."""

import time
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from todo_mcp.api.openai_compat import (
    ChatMessage,
    OpenAIChatRequest,
    OpenAIChatResponse,
    Usage,
    Choice,
    ModelInfo,
    ModelList,
    convert_openai_messages,
)


def test_chat_message_creation():
    """Test basic ChatMessage creation."""
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.name is None


def test_chat_message_with_name():
    """Test ChatMessage with optional name field."""
    msg = ChatMessage(role="assistant", content="Hi there", name="bot")
    assert msg.role == "assistant"
    assert msg.content == "Hi there"
    assert msg.name == "bot"


def test_openai_chat_request():
    """Test OpenAIChatRequest model."""
    messages = [
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="Hello!"),
    ]
    request = OpenAIChatRequest(
        model="todo-agent",
        messages=messages,
        temperature=0.7,
        max_tokens=100,
    )
    assert request.model == "todo-agent"
    assert len(request.messages) == 2
    assert request.temperature == 0.7
    assert request.max_tokens == 100
    assert request.user is None


def test_openai_chat_response():
    """Test OpenAIChatResponse model."""
    now = int(time.time())
    response = OpenAIChatResponse(
        id="chatcmpl-123",
        created=now,
        model="todo-agent",
        choices=[
            Choice(
                index=0,
                message=ChatMessage(role="assistant", content="Hello!"),
                finish_reason="stop",
            )
        ],
    )
    assert response.id == "chatcmpl-123"
    assert response.object == "chat.completion"
    assert response.created == now
    assert response.model == "todo-agent"
    assert len(response.choices) == 1
    assert response.choices[0].message.content == "Hello!"
    assert response.usage.total_tokens == 0


def test_usage_defaults():
    """Test Usage model with default values."""
    usage = Usage()
    assert usage.prompt_tokens == 0
    assert usage.completion_tokens == 0
    assert usage.total_tokens == 0


def test_usage_with_values():
    """Test Usage model with custom values."""
    usage = Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    assert usage.prompt_tokens == 10
    assert usage.completion_tokens == 20
    assert usage.total_tokens == 30


def test_model_info():
    """Test ModelInfo model."""
    now = int(time.time())
    model = ModelInfo(id="todo-agent", created=now)
    assert model.id == "todo-agent"
    assert model.object == "model"
    assert model.created == now
    assert model.owned_by == "local"


def test_model_list():
    """Test ModelList model."""
    now = int(time.time())
    models = ModelList(
        data=[
            ModelInfo(id="todo-agent", created=now),
            ModelInfo(id="todo-agent-v2", created=now),
        ]
    )
    assert models.object == "list"
    assert len(models.data) == 2
    assert models.data[0].id == "todo-agent"


def test_convert_openai_messages_single():
    """Test conversion with a single user message."""
    messages = [ChatMessage(role="user", content="Hello")]
    session_id, user_message = convert_openai_messages(messages)
    assert session_id == "default"
    assert user_message == "Hello"


def test_convert_openai_messages_with_system():
    """Test that system messages are ignored."""
    messages = [
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="What can you do?"),
    ]
    session_id, user_message = convert_openai_messages(messages)
    assert session_id == "default"
    assert user_message == "What can you do?"


def test_convert_openai_messages_conversation():
    """Test multi-turn conversation extracts last user message."""
    messages = [
        ChatMessage(role="user", content="First message"),
        ChatMessage(role="assistant", content="Response 1"),
        ChatMessage(role="user", content="Second message"),
        ChatMessage(role="assistant", content="Response 2"),
        ChatMessage(role="user", content="Latest question"),
    ]
    session_id, user_message = convert_openai_messages(messages)
    assert session_id == "default"
    assert user_message == "Latest question"


def test_convert_openai_messages_empty():
    """Test empty list returns default values."""
    messages = []
    session_id, user_message = convert_openai_messages(messages)
    assert session_id == "default"
    assert user_message == ""


@pytest.fixture
def client():
    """Create test client with OpenAI compat router."""
    from fastapi import FastAPI
    from todo_mcp.api.openai_compat import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestModelsEndpoint:
    """Tests for /v1/models endpoints."""

    def test_list_models(self, client):
        """Test listing available models."""
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert any(m["id"] == "todo-agent" for m in data["data"])

    def test_get_model(self, client):
        """Test getting a specific model."""
        response = client.get("/v1/models/todo-agent")
        assert response.status_code == 200
        assert response.json()["id"] == "todo-agent"

    def test_get_model_not_found(self, client):
        """Test getting a non-existent model."""
        response = client.get("/v1/models/nonexistent")
        assert response.status_code == 404


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
                        "messages": [{"role": "user", "content": "今天有什么任务？"}]
                    }
                )

        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "chat.completion"
        assert data["model"] == "todo-agent"
        assert len(data["choices"]) == 1
        assert data["choices"][0]["message"]["role"] == "assistant"

    def test_chat_completions_response_structure(self, client):
        """Test response has all required OpenAI fields."""
        with patch("todo_mcp.api.openai_compat.get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_get_agent.return_value = mock_agent

            with patch("todo_mcp.api.openai_compat.run_agent") as mock_run:
                mock_run.return_value = "响应内容"

                response = client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "todo-agent",
                        "messages": [{"role": "user", "content": "测试"}]
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
                        "messages": [{"role": "user", "content": "测试"}],
                        "user": "custom-session"
                    }
                )

        assert response.status_code == 200
        mock_run.assert_called_once()
        # The third argument (session_manager) has the session
        call_args = mock_run.call_args
        assert "custom-session" in str(call_args)


class TestServerIntegration:
    """Test OpenAI endpoints integrated with main server."""

    @pytest.fixture
    def server_client(self):
        from todo_mcp.api.server import create_app
        from fastapi.testclient import TestClient
        app = create_app()
        return TestClient(app)

    def test_openai_routes_included(self, server_client):
        """Test OpenAI routes are included in main server."""
        response = server_client.get("/v1/models")
        assert response.status_code == 200

    def test_openai_chat_on_main_server(self, server_client):
        """Test chat completions on main server."""
        with patch("todo_mcp.api.openai_compat.get_agent") as mock_get:
            mock_agent = MagicMock()
            mock_get.return_value = mock_agent

            with patch("todo_mcp.api.openai_compat.run_agent") as mock_run:
                mock_run.return_value = "集成测试响应"

                response = server_client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "todo-agent",
                        "messages": [{"role": "user", "content": "测试"}]
                    }
                )

        assert response.status_code == 200
        assert "集成测试响应" in response.json()["choices"][0]["message"]["content"]
