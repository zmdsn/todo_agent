# OpenAI 兼容 API 设计

> 日期: 2026-03-12

## 目标

为 Todo Agent 添加 OpenAI 兼容的 API 端点，使外部应用可以直接使用 OpenAI SDK 调用。

## 需求

- 完全兼容 OpenAI Chat Completions API
- 仅支持同步模式（不支持流式）
- 不暴露 Function Calling（Agent 内部自动处理）
- 可用 OpenAI SDK 直接调用

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Server                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐    ┌──────────────────────────────┐   │
│  │  /chat           │    │  /v1/chat/completions        │   │
│  │  (原有端点)       │    │  (OpenAI 兼容)               │   │
│  └────────┬─────────┘    └──────────────┬───────────────┘   │
│           │                               │                  │
│           └───────────────┬───────────────┘                  │
│                           ▼                                  │
│              ┌────────────────────────┐                      │
│              │     Todo Agent         │                      │
│              │  (LangChain/LangGraph) │                      │
│              └────────────────────────┘                      │
│                           │                                  │
│                           ▼                                  │
│              ┌────────────────────────┐                      │
│              │    Tools + Memory      │                      │
│              └────────────────────────┘                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/chat/completions` | POST | 聊天补全（核心） |
| `/v1/models` | GET | 列出可用模型 |
| `/v1/models/{model_id}` | GET | 获取模型信息 |

## 数据模型

### 请求

```python
from pydantic import BaseModel
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
    user: Optional[str] = None  # 映射到 session_id
```

### 响应

```python
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
    usage: Usage = Usage()
```

## 核心实现

### 消息转换

```python
def convert_openai_messages(messages: list[ChatMessage]) -> tuple[str, str]:
    """将 OpenAI 消息格式转换为 Agent 输入。

    Returns:
        (session_id, user_message)
    """
    # 从 messages 中提取：
    # - system 消息 → 忽略（Agent 已有内置 system prompt）
    # - user 消息 → 最后一条作为当前输入
    # - user 字段 → 作为 session_id

    session_id = "default"
    user_message = ""

    # 最后一条 user 消息作为输入
    for msg in reversed(messages):
        if msg.role == "user":
            user_message = msg.content
            break

    return session_id, user_message
```

### 端点实现

```python
import time
import uuid
from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])


@router.post("/chat/completions", response_model=OpenAIChatResponse)
async def chat_completions(request: OpenAIChatRequest):
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


@router.get("/models")
async def list_models():
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
async def get_model(model_id: str):
    """获取模型信息。"""
    if model_id != "todo-agent":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Model not found")

    return {
        "id": "todo-agent",
        "object": "model",
        "created": 1700000000,
        "owned_by": "local"
    }
```

## 项目结构

```
todo-mcp/
├── src/todo_mcp/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py           # 现有服务（保留）
│   │   └── openai_compat.py    # 新增：OpenAI 兼容层
│   └── ...
```

### server.py 修改

```python
# 在 create_app() 中添加：
from todo_mcp.api.openai_compat import router as openai_router

app.include_router(openai_router)
```

## 使用示例

### 使用 OpenAI SDK

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

### 使用 curl

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "todo-agent",
    "messages": [{"role": "user", "content": "添加任务：完成报告"}]
  }'
```

### 响应示例

```json
{
  "id": "chatcmpl-abc123def456",
  "object": "chat.completion",
  "created": 1710123456,
  "model": "todo-agent",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "已添加任务「完成报告」到今日计划。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  }
}
```

## 测试计划

1. **端点测试**
   - POST /v1/chat/completions 返回正确格式
   - GET /v1/models 返回模型列表
   - GET /v1/models/{model_id} 返回模型信息

2. **兼容性测试**
   - OpenAI SDK 可以正常调用
   - 错误响应格式正确

3. **集成测试**
   - 会话管理正常工作
   - Agent 工具调用正常

## 依赖

无需新增依赖，使用现有 FastAPI 和 Pydantic。
