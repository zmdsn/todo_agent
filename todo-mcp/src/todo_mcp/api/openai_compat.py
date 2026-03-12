"""OpenAI-compatible data models for chat completions API."""

import time
import uuid
from typing import Literal, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from todo_mcp.agent import create_todo_agent, run_agent, session_manager


router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])


# Global agent instance and config
_agent = None
_config = {
    "base_url": "http://localhost:11434/v1",
    "model": "qwen2.5",
    "temperature": 0.7,
    "api_key": "dummy"
}


def set_config(base_url: str, model: str, temperature: float = 0.7, api_key: str = "dummy"):
    """设置 Agent 配置。"""
    global _config, _agent
    _config = {
        "base_url": base_url,
        "model": model,
        "temperature": temperature,
        "api_key": api_key
    }
    # 重置 agent 以使用新配置
    _agent = None


def get_agent():
    """获取或创建 agent 实例。"""
    global _agent
    if _agent is None:
        _agent = create_todo_agent(
            base_url=_config["base_url"],
            model=_config["model"],
            temperature=_config["temperature"],
            api_key=_config["api_key"]
        )
    return _agent


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
