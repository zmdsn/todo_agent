# Todo Agent 设计文档

> 日期: 2026-03-10

## 目标

将 todo-mcp 从 MCP Server 形式改造为独立的智能体形式，支持多轮对话和智能建议。

## 需求

- 独立智能体形式（非 MCP Server）
- 支持命令行多轮对话 + HTTP API
- 使用兼容 OpenAI 格式的 LLM（Ollama、vLLM 等）
- 完整能力：基础任务管理 + 分析 + 智能建议

## 架构

```
┌─────────────────────────────────────────────┐
│                  Todo Agent                  │
├─────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────────────┐  │
│  │  CLI 接口   │    │     HTTP API        │  │
│  │  (多轮对话) │    │  (FastAPI/Starlette)│  │
│  └──────┬──────┘    └──────────┬──────────┘  │
│         │                      │             │
│         └──────────┬───────────┘             │
│                    ▼                         │
│         ┌─────────────────────┐              │
│         │   LangChain Agent   │              │
│         │   + Memory (对话历史) │              │
│         └──────────┬──────────┘              │
│                    ▼                         │
│         ┌─────────────────────┐              │
│         │   Tools (复用现有)    │              │
│         │   add_task          │              │
│         │   get_today         │              │
│         │   update_task       │              │
│         │   analyze_status    │              │
│         │   suggest_schedule  │ (新增)       │
│         │   prioritize_tasks  │ (新增)       │
│         └──────────┬──────────┘              │
│                    ▼                         │
│         ┌─────────────────────┐              │
│         │   核心业务逻辑        │              │
│         │   (复用 todo-mcp)    │              │
│         └─────────────────────┘              │
└─────────────────────────────────────────────┘
```

## 核心组件

### LLM 配置

```python
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationBufferMemory

llm = ChatOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="dummy",
    model="qwen2.5"
)

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)
```

### 工具层

| 工具 | 来源 | 说明 |
|------|------|------|
| add_task | 复用 | 添加任务 |
| get_today | 复用 | 今日概览 |
| update_task | 复用 | 更新任务 |
| list_plans | 复用 | 列出计划 |
| get_progress | 复用 | 获取进度 |
| analyze_status | 复用 | 健康分析 |
| suggest_schedule | 新增 | 智能安排建议 |
| prioritize_tasks | 新增 | 优先级建议 |

## 接口设计

### CLI 模式

```bash
# 启动交互式对话
todo-agent chat

# 指定模型
todo-agent chat --model qwen2.5 --base-url http://localhost:11434/v1
```

### HTTP API 模式

```bash
# 启动 API 服务
todo-agent serve --port 8080

# API 调用
POST /chat
{
  "message": "今天有什么任务？",
  "session_id": "user-123"
}
```

### 配置文件

```yaml
llm:
  base_url: http://localhost:11434/v1
  model: qwen2.5
  temperature: 0.7

todo_root: ~/todo
default_reminder_days: 3
```

## 项目结构

```
todo-mcp/
├── src/todo_mcp/
│   ├── __init__.py
│   ├── agent/                 # Agent 相关
│   │   ├── __init__.py
│   │   ├── agent.py           # LangChain Agent 定义
│   │   ├── tools.py           # 工具封装
│   │   ├── prompts.py         # 系统提示词
│   │   └── memory.py          # 会话记忆管理
│   ├── cli/                   # 命令行接口
│   │   ├── __init__.py
│   │   └── main.py            # CLI 入口
│   ├── api/                   # HTTP API
│   │   ├── __init__.py
│   │   └── server.py          # FastAPI 服务
│   ├── models/                # 数据模型
│   ├── parser/                # Markdown 读写
│   ├── utils/                 # 工具函数
│   └── server.py              # MCP Server（保留）
├── pyproject.toml
└── config.yaml
```

## 依赖

```toml
langchain>=0.3.0
langchain-openai>=0.2.0
langchain-community>=0.3.0
click>=8.0.0
fastapi>=0.115.0
uvicorn>=0.30.0
```
