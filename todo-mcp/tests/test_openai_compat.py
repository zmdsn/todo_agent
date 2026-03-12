"""Tests for OpenAI compatible data models."""

import time
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
