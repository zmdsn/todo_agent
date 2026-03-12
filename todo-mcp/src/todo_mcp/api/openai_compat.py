"""OpenAI-compatible data models for chat completions API."""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""

    role: Literal["system", "user", "assistant"]
    content: str
    name: Optional[str] = None


class OpenAIChatRequest(BaseModel):
    """Request model for OpenAI chat completions API."""

    model: str = "todo-agent"
    messages: list[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    user: Optional[str] = None


class Usage(BaseModel):
    """Token usage statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class Choice(BaseModel):
    """A single completion choice."""

    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class OpenAIChatResponse(BaseModel):
    """Response model for OpenAI chat completions API."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage = Field(default_factory=Usage)


class ModelInfo(BaseModel):
    """Information about a model."""

    id: str
    object: str = "model"
    created: int
    owned_by: str = "local"


class ModelList(BaseModel):
    """List of available models."""

    object: str = "list"
    data: list[ModelInfo]


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
