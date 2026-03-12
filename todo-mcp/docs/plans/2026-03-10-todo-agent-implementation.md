# Todo Agent 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 todo-mcp 从 MCP Server 改造为独立智能体，支持多轮对话和智能建议。

**Architecture:** 使用 LangChain 构建智能体，复用现有的业务逻辑（models/parser/utils），新增 CLI 和 HTTP API 接口。

**Tech Stack:** LangChain, LangChain-OpenAI, Click, FastAPI, Uvicorn

---

## Task 1: 添加依赖

**Files:**
- Modify: `todo-mcp/pyproject.toml`

**Step 1: 更新 pyproject.toml**

在 dependencies 中添加：

```toml
[project]
name = "todo-mcp"
version = "0.2.0"
description = "Personal plan management agent"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "mcp>=1.26.0",
    "pydantic>=2.12.5",
    "pytest>=9.0.2",
    "pytest-asyncio>=1.3.0",
    "python-dateutil>=2.9.0.post0",
    "starlette>=0.40.0",
    "uvicorn>=0.30.0",
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",
    "click>=8.0.0",
    "fastapi>=0.115.0",
]

[project.scripts]
todo-mcp = "todo_mcp.server:main"
todo-agent = "todo_mcp.cli.main:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.uv]
package = true
```

**Step 2: 同步依赖**

Run: `cd /home/zmdsn/todo/todo-mcp && uv sync`
Expected: 依赖安装成功

**Step 3: 提交**

```bash
git add pyproject.toml
git commit -m "chore: add langchain and cli dependencies"
```

---

## Task 2: 创建 Agent 工具封装

**Files:**
- Create: `todo-mcp/src/todo_mcp/agent/__init__.py`
- Create: `todo-mcp/src/todo_mcp/agent/tools.py`

**Step 1: 创建 agent 目录和 __init__.py**

```python
# todo-mcp/src/todo_mcp/agent/__init__.py
"""Todo Agent module."""
from .tools import get_all_tools

__all__ = ["get_all_tools"]
```

**Step 2: 创建 tools.py**

```python
# todo-mcp/src/todo_mcp/agent/tools.py
"""LangChain tools for todo agent."""
from langchain_core.tools import tool
from typing import Optional, List
from pathlib import Path

from todo_mcp.models import Task, TaskStatus, Config
from todo_mcp.utils.time import TimeParser
from todo_mcp.parser.writer import MarkdownWriter
from todo_mcp.parser.reader import MarkdownReader
from datetime import date


def _get_config() -> Config:
    """Get config instance."""
    return Config()


@tool
def add_task(content: str, time_expr: str, priority: Optional[str] = None) -> str:
    """添加任务到指定时间。

    Args:
        content: 任务内容
        time_expr: 时间表达式，如"今天"、"明天"、"本周"、"3月15日"
        priority: 优先级，可选值: high, medium, low

    Returns:
        操作结果消息
    """
    config = _get_config()
    parser = TimeParser()
    parsed = parser.parse(time_expr)

    file_path_str = parsed.to_file_path()
    if "#" in file_path_str:
        file_path_str = file_path_str.split("#")[0]
    file_path = config.todo_root / file_path_str

    writer = MarkdownWriter(file_path)
    if not file_path.exists():
        writer.ensure_file_exists(parsed.year, parsed.quarter, parsed.month)

    # 简单生成 ID
    task_id = f"{parsed.year}-{parsed.quarter}-{parsed.month}"

    task = Task(
        id=task_id,
        content=content,
        status=TaskStatus.PENDING,
        location=str(file_path),
        priority=priority
    )

    writer.add_task(task, day=parsed.day)
    return f"已添加任务: {content} 到 {time_expr}"


@tool
def get_today() -> str:
    """获取今日任务概览。

    Returns:
        今日任务列表和统计信息
    """
    config = _get_config()
    today = date.today()
    parser = TimeParser()
    parsed = parser.parse("今天")

    file_path_str = parsed.to_file_path()
    if "#" in file_path_str:
        file_path_str = file_path_str.split("#")[0]
    file_path = config.todo_root / file_path_str

    if not file_path.exists():
        return f"📅 今日概览 ({today.year}/{today.month}/{today.day})\n\n今日暂无任务安排 🎉"

    reader = MarkdownReader(file_path)
    tasks = reader.read_tasks()

    # 筛选今日任务
    today_tasks = []
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    current_day = None
    task_counter = 0

    for line in lines:
        day = reader._parse_day_header(line.strip())
        if day is not None:
            current_day = day
            task_counter = 0
            continue

        task_match = MarkdownReader.TASK_PATTERN.match(line.strip())
        if task_match and current_day == today.day:
            task_counter += 1
            status = TaskStatus.COMPLETED if task_match.group(2).lower() == 'x' else TaskStatus.PENDING
            task = Task(
                id=f"{today.year}-{parsed.quarter}-{today.month:02d}-{today.day:02d}-{task_counter}",
                content=task_match.group(3).strip(),
                status=status,
                location=str(file_path)
            )
            today_tasks.append(task)

    total = len(today_tasks)
    completed = sum(1 for t in today_tasks if t.status == TaskStatus.COMPLETED)
    pending = total - completed

    result = f"📅 今日概览 ({today.year}/{today.month}/{today.day})\n\n"
    result += f"📊 统计: 总计 {total} 项任务, 已完成 {completed} 项, 待办 {pending} 项\n\n"

    if today_tasks:
        result += "📋 任务列表:\n"
        for task in today_tasks:
            status_icon = "✅" if task.status == TaskStatus.COMPLETED else "⬜"
            result += f"  {status_icon} {task.content}\n"
    else:
        result += "今日暂无任务安排 🎉"

    return result


@tool
def list_plans(time_expr: str = "本月", include_completed: bool = True) -> str:
    """列出指定时间范围的计划。

    Args:
        time_expr: 时间范围，如"今天"、"本周"、"本月"
        include_completed: 是否包含已完成任务

    Returns:
        计划列表
    """
    config = _get_config()
    parser = TimeParser()
    parsed = parser.parse(time_expr)

    file_path_str = parsed.to_file_path()
    if "#" in file_path_str:
        file_path_str = file_path_str.split("#")[0]
    file_path = config.todo_root / file_path_str

    if not file_path.exists():
        return f"📋 计划列表 ({time_expr})\n\n暂无计划项"

    reader = MarkdownReader(file_path)
    tasks = reader.read_tasks()

    if not include_completed:
        tasks = [t for t in tasks if t.status != TaskStatus.COMPLETED]

    result = f"📋 计划列表 ({time_expr})\n\n"

    if not tasks:
        result += "暂无计划项"
    else:
        for i, task in enumerate(tasks, 1):
            status_icon = "✅" if task.status == TaskStatus.COMPLETED else "⬜"
            result += f"{i}. {status_icon} {task.content}\n"

    return result


@tool
def update_task(task_id: str, status: Optional[str] = None) -> str:
    """更新任务状态。

    Args:
        task_id: 任务ID
        status: 新状态，可选值: completed, pending

    Returns:
        操作结果消息
    """
    config = _get_config()

    # 解析 task_id 获取文件路径
    try:
        parts = task_id.split("-")
        if len(parts) >= 4:
            year = parts[0]
            quarter = parts[1].replace("Q", "") if "Q" in parts[1] else parts[1]
            month = parts[2] if "Q" in parts[1] else parts[1]

            month_names = {
                "01": "01-January", "02": "02-February", "03": "03-March",
                "04": "04-April", "05": "05-May", "06": "06-June",
                "07": "07-July", "08": "08-August", "09": "09-September",
                "10": "10-October", "11": "11-November", "12": "12-December"
            }
            month_file = month_names.get(month, f"{month}-Month")
            file_path = config.todo_root / year / f"Q{quarter}" / f"{month_file}.md"

            if not file_path.exists():
                return f"错误: 找不到任务文件"

            writer = MarkdownWriter(file_path)

            if status:
                new_status = TaskStatus.COMPLETED if status.lower() in ["completed", "done", "完成"] else TaskStatus.PENDING
                success = writer.update_task_status(task_id, new_status)
                if success:
                    return f"任务状态已更新为: {new_status.value}"
                else:
                    return "更新任务状态失败"

            return "任务已更新"
        else:
            return f"错误: 无效的 task_id 格式: {task_id}"
    except Exception as e:
        return f"错误: {str(e)}"


@tool
def get_progress(time_expr: str = "本月") -> str:
    """获取完成进度。

    Args:
        time_expr: 时间范围，如"今天"、"本周"、"本月"

    Returns:
        进度统计信息
    """
    config = _get_config()
    parser = TimeParser()
    parsed = parser.parse(time_expr)

    file_path_str = parsed.to_file_path()
    if "#" in file_path_str:
        file_path_str = file_path_str.split("#")[0]
    file_path = config.todo_root / file_path_str

    if not file_path.exists():
        return f"📈 进度报告 ({time_expr})\n\n暂无数据"

    reader = MarkdownReader(file_path)
    tasks = reader.read_tasks()

    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
    pending = total - completed
    progress = (completed / total * 100) if total > 0 else 0

    result = f"📈 进度报告 ({time_expr})\n\n"
    result += f"📊 统计:\n"
    result += f"  - 总任务: {total} 项\n"
    result += f"  - 已完成: {completed} 项\n"
    result += f"  - 待办: {pending} 项\n"
    result += f"  - 完成率: {progress:.1f}%\n"

    bar_length = 20
    filled = int(bar_length * progress / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    result += f"\n进度: [{bar}] {progress:.1f}%\n"

    return result


@tool
def analyze_status(time_expr: str = "本月") -> str:
    """分析计划健康状态。

    Args:
        time_expr: 时间范围，默认为"本月"

    Returns:
        健康状态分析和建议
    """
    config = _get_config()
    parser = TimeParser()
    parsed = parser.parse(time_expr)

    file_path_str = parsed.to_file_path()
    if "#" in file_path_str:
        file_path_str = file_path_str.split("#")[0]
    file_path = config.todo_root / file_path_str

    if not file_path.exists():
        return f"计划文件不存在: {time_expr}"

    reader = MarkdownReader(file_path)
    tasks = reader.read_tasks()

    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
    pending = total - completed
    progress = (completed / total * 100) if total > 0 else 0

    if progress >= 80:
        health = "优秀"
        emoji = "🌟"
    elif progress >= 60:
        health = "良好"
        emoji = "👍"
    elif progress >= 40:
        health = "一般"
        emoji = "⚠️"
    else:
        health = "需要关注"
        emoji = "🔴"

    result = f"📊 计划健康状态分析 ({time_expr})\n\n"
    result += f"{emoji} 健康度: {health}\n\n"
    result += f"📈 统计数据:\n"
    result += f"  - 总任务: {total} 项\n"
    result += f"  - 已完成: {completed} 项\n"
    result += f"  - 待办: {pending} 项\n"
    result += f"  - 完成率: {progress:.1f}%\n\n"

    result += "💡 建议:\n"
    if progress < 50:
        result += "  - 建议重新评估任务优先级\n"
        result += "  - 考虑拆分大任务为小任务\n"
    elif progress < 80:
        result += "  - 继续保持当前节奏\n"
        result += "  - 关注即将到期的任务\n"
    else:
        result += "  - 表现优秀，继续保持!\n"
        result += "  - 可以考虑增加更多挑战性任务\n"

    return result


@tool
def suggest_schedule() -> str:
    """智能安排建议，基于当前任务情况给出优化建议。

    Returns:
        智能安排建议
    """
    config = _get_config()
    today = date.today()
    parser = TimeParser()

    # 获取本月任务
    parsed = parser.parse("本月")
    file_path_str = parsed.to_file_path()
    if "#" in file_path_str:
        file_path_str = file_path_str.split("#")[0]
    file_path = config.todo_root / file_path_str

    if not file_path.exists():
        return "💡 暂无任务数据，请先添加任务"

    reader = MarkdownReader(file_path)
    tasks = reader.read_tasks()

    pending_tasks = [t for t in tasks if t.status == TaskStatus.PENDING]

    if not pending_tasks:
        return "🎉 所有任务已完成！本周可以安排一些新目标。"

    result = "💡 智能安排建议\n\n"

    # 按优先级分组
    high_priority = [t for t in pending_tasks if t.priority == "high"]
    medium_priority = [t for t in pending_tasks if t.priority == "medium"]
    low_priority = [t for t in pending_tasks if t.priority == "low" or t.priority is None]

    result += "📋 待办任务优先级分布:\n"
    result += f"  - 高优先级: {len(high_priority)} 项\n"
    result += f"  - 中优先级: {len(medium_priority)} 项\n"
    result += f"  - 低优先级: {len(low_priority)} 项\n\n"

    result += "📅 建议安排:\n"
    if high_priority:
        result += f"  1. 首先处理高优先级任务（{len(high_priority)}项）\n"
        for t in high_priority[:3]:
            result += f"     - {t.content}\n"
    if medium_priority:
        result += f"  2. 其次处理中优先级任务（{len(medium_priority)}项）\n"
    if low_priority:
        result += f"  3. 最后处理低优先级任务（{len(low_priority)}项）\n"

    result += f"\n⏰ 建议每天处理 2-3 个任务，预计 {len(pending_tasks) // 2 + 1} 天完成所有待办。"

    return result


def get_all_tools():
    """获取所有工具列表。"""
    return [
        add_task,
        get_today,
        list_plans,
        update_task,
        get_progress,
        analyze_status,
        suggest_schedule,
    ]
```

**Step 3: 验证导入**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run python -c "from todo_mcp.agent.tools import get_all_tools; print(len(get_all_tools()))"`
Expected: `7`

**Step 4: 提交**

```bash
git add src/todo_mcp/agent/
git commit -m "feat: add langchain tools for todo agent"
```

---

## Task 3: 创建 Agent 核心逻辑

**Files:**
- Create: `todo-mcp/src/todo_mcp/agent/prompts.py`
- Create: `todo-mcp/src/todo_mcp/agent/memory.py`
- Create: `todo-mcp/src/todo_mcp/agent/agent.py`

**Step 1: 创建 prompts.py**

```python
# todo-mcp/src/todo_mcp/agent/prompts.py
"""System prompts for todo agent."""

SYSTEM_PROMPT = """你是一个个人计划管理助手，帮助用户管理日常任务和计划。

你可以帮助用户：
- 添加、查看、更新任务
- 分析任务完成进度
- 提供智能安排建议

请用简洁友好的中文回复用户。当用户提到时间时，理解各种表达方式如"今天"、"明天"、"下周"、"3月15日"等。

当前日期: {current_date}
"""

def get_system_prompt() -> str:
    """获取系统提示词。"""
    from datetime import date
    today = date.today()
    return SYSTEM_PROMPT.format(current_date=today.strftime("%Y年%m月%d日"))
```

**Step 2: 创建 memory.py**

```python
# todo-mcp/src/todo_mcp/agent/memory.py
"""Memory management for todo agent."""
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage
from typing import Dict, List
import threading


class SessionManager:
    """管理多个会话的记忆。"""

    def __init__(self, max_sessions: int = 100):
        self._sessions: Dict[str, ConversationBufferMemory] = {}
        self._lock = threading.Lock()
        self._max_sessions = max_sessions

    def get_memory(self, session_id: str) -> ConversationBufferMemory:
        """获取或创建会话记忆。"""
        with self._lock:
            if session_id not in self._sessions:
                # 清理旧会话
                if len(self._sessions) >= self._max_sessions:
                    oldest = next(iter(self._sessions))
                    del self._sessions[oldest]

                self._sessions[session_id] = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True
                )
            return self._sessions[session_id]

    def clear_session(self, session_id: str) -> None:
        """清除指定会话。"""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]

    def get_history(self, session_id: str) -> List[BaseMessage]:
        """获取会话历史。"""
        memory = self.get_memory(session_id)
        return memory.chat_memory.messages


# 全局会话管理器
session_manager = SessionManager()
```

**Step 3: 创建 agent.py**

```python
# todo-mcp/src/todo_mcp/agent/agent.py
"""LangChain agent for todo management."""
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Optional

from .tools import get_all_tools
from .prompts import get_system_prompt
from .memory import SessionManager


def create_todo_agent(
    base_url: str = "http://localhost:11434/v1",
    model: str = "qwen2.5",
    temperature: float = 0.7,
    api_key: str = "dummy"
):
    """创建 Todo Agent。

    Args:
        base_url: LLM API 地址
        model: 模型名称
        temperature: 温度参数
        api_key: API 密钥

    Returns:
        AgentExecutor 实例
    """
    llm = ChatOpenAI(
        base_url=base_url,
        model=model,
        temperature=temperature,
        api_key=api_key
    )

    tools = get_all_tools()

    prompt = ChatPromptTemplate.from_messages([
        ("system", get_system_prompt()),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
    )


def run_agent(
    agent: AgentExecutor,
    message: str,
    session_manager: SessionManager,
    session_id: str = "default"
) -> str:
    """运行 Agent 并返回响应。

    Args:
        agent: AgentExecutor 实例
        message: 用户消息
        session_manager: 会话管理器
        session_id: 会话ID

    Returns:
        Agent 响应
    """
    memory = session_manager.get_memory(session_id)
    chat_history = memory.chat_memory.messages

    result = agent.invoke({
        "input": message,
        "chat_history": chat_history
    })

    # 保存到记忆
    memory.chat_memory.add_user_message(message)
    memory.chat_memory.add_ai_message(result["output"])

    return result["output"]
```

**Step 4: 更新 __init__.py**

```python
# todo-mcp/src/todo_mcp/agent/__init__.py
"""Todo Agent module."""
from .tools import get_all_tools
from .agent import create_todo_agent, run_agent
from .memory import SessionManager, session_manager
from .prompts import get_system_prompt

__all__ = [
    "get_all_tools",
    "create_todo_agent",
    "run_agent",
    "SessionManager",
    "session_manager",
    "get_system_prompt"
]
```

**Step 5: 验证**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run python -c "from todo_mcp.agent import create_todo_agent; print('OK')"`
Expected: `OK`

**Step 6: 提交**

```bash
git add src/todo_mcp/agent/
git commit -m "feat: add agent core logic with memory support"
```

---

## Task 4: 创建 CLI 接口

**Files:**
- Create: `todo-mcp/src/todo_mcp/cli/__init__.py`
- Create: `todo-mcp/src/todo_mcp/cli/main.py`

**Step 1: 创建 cli 目录**

```python
# todo-mcp/src/todo_mcp/cli/__init__.py
"""CLI module for todo agent."""
```

**Step 2: 创建 main.py**

```python
# todo-mcp/src/todo_mcp/cli/main.py
"""CLI interface for todo agent."""
import click
import sys
from pathlib import Path

from todo_mcp.agent import create_todo_agent, run_agent, session_manager
from todo_mcp.models import Config


def load_config() -> Config:
    """加载配置。"""
    # 查找配置文件
    config_paths = [
        Path.cwd() / "config.yaml",
        Path.home() / ".config" / "todo-agent" / "config.yaml",
    ]

    for path in config_paths:
        if path.exists():
            import yaml
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            return Config(**data.get("todo", {}))

    return Config()


@click.group()
@click.version_option(version="0.2.0")
def main():
    """Todo Agent - 个人计划管理智能助手。"""
    pass


@main.command()
@click.option("--model", "-m", default="qwen2.5", help="LLM 模型名称")
@click.option("--base-url", "-u", default="http://localhost:11434/v1", help="LLM API 地址")
@click.option("--temperature", "-t", default=0.7, help="温度参数")
def chat(model: str, base_url: str, temperature: float):
    """启动交互式对话。"""
    click.echo(f"🤖 Todo Agent 启动中...")
    click.echo(f"   模型: {model}")
    click.echo(f"   API: {base_url}")
    click.echo(f"   输入 'quit' 或 'exit' 退出\n")

    try:
        agent = create_todo_agent(
            base_url=base_url,
            model=model,
            temperature=temperature
        )
    except Exception as e:
        click.echo(f"❌ 无法连接到 LLM: {e}", err=True)
        sys.exit(1)

    click.echo("💬 开始对话吧！\n")

    while True:
        try:
            user_input = click.prompt("你", type=str).strip()
        except (KeyboardInterrupt, EOFError):
            click.echo("\n👋 再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "q"]:
            click.echo("👋 再见！")
            break

        if user_input.lower() in ["clear", "reset"]:
            session_manager.clear_session("cli")
            click.echo("🔄 会话已重置\n")
            continue

        try:
            response = run_agent(agent, user_input, session_manager, "cli")
            click.echo(f"\n🤖 {response}\n")
        except Exception as e:
            click.echo(f"❌ 错误: {e}\n")


@main.command()
@click.option("--port", "-p", default=8080, help="服务端口")
@click.option("--host", "-h", default="127.0.0.1", help="绑定地址")
@click.option("--model", "-m", default="qwen2.5", help="LLM 模型名称")
@click.option("--base-url", "-u", default="http://localhost:11434/v1", help="LLM API 地址")
def serve(port: int, host: str, model: str, base_url: str):
    """启动 HTTP API 服务。"""
    import uvicorn
    from todo_mcp.api.server import create_app

    click.echo(f"🚀 启动 API 服务...")
    click.echo(f"   地址: http://{host}:{port}")
    click.echo(f"   模型: {model}")
    click.echo(f"   API: {base_url}")

    app = create_app(model=model, base_url=base_url)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
```

**Step 3: 验证 CLI**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run todo-agent --help`
Expected: 显示帮助信息

**Step 4: 提交**

```bash
git add src/todo_mcp/cli/
git commit -m "feat: add CLI interface for todo agent"
```

---

## Task 5: 创建 HTTP API

**Files:**
- Create: `todo-mcp/src/todo_mcp/api/__init__.py`
- Create: `todo-mcp/src/todo_mcp/api/server.py`

**Step 1: 创建 api 目录**

```python
# todo-mcp/src/todo_mcp/api/__init__.py
"""API module for todo agent."""
```

**Step 2: 创建 server.py**

```python
# todo-mcp/src/todo_mcp/api/server.py
"""FastAPI server for todo agent."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid

from todo_mcp.agent import create_todo_agent, run_agent, session_manager


class ChatRequest(BaseModel):
    """聊天请求。"""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应。"""
    response: str
    session_id: str


# 全局 agent 实例
_agent = None
_config = {}


def get_agent():
    """获取或创建 agent 实例。"""
    global _agent
    if _agent is None:
        _agent = create_todo_agent(
            base_url=_config.get("base_url", "http://localhost:11434/v1"),
            model=_config.get("model", "qwen2.5"),
            temperature=_config.get("temperature", 0.7)
        )
    return _agent


def create_app(model: str = "qwen2.5", base_url: str = "http://localhost:11434/v1", temperature: float = 0.7):
    """创建 FastAPI 应用。"""
    global _config
    _config = {
        "model": model,
        "base_url": base_url,
        "temperature": temperature
    }

    app = FastAPI(
        title="Todo Agent API",
        description="个人计划管理智能助手 API",
        version="0.2.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        """健康检查。"""
        return {"status": "ok", "service": "todo-agent"}

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        """处理聊天请求。"""
        session_id = request.session_id or str(uuid.uuid4())

        try:
            agent = get_agent()
            response = run_agent(agent, request.message, session_manager, session_id)
            return ChatResponse(response=response, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/session/{session_id}")
    async def clear_session(session_id: str):
        """清除会话。"""
        session_manager.clear_session(session_id)
        return {"status": "ok", "message": "Session cleared"}

    @app.get("/tools")
    async def list_tools():
        """列出可用工具。"""
        from todo_mcp.agent import get_all_tools
        tools = get_all_tools()
        return {
            "tools": [
                {"name": t.name, "description": t.description}
                for t in tools
            ]
        }

    return app


# 用于 uvicorn 直接运行
app = create_app()
```

**Step 3: 验证 API**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run python -c "from todo_mcp.api.server import create_app; print('OK')"`
Expected: `OK`

**Step 4: 提交**

```bash
git add src/todo_mcp/api/
git commit -m "feat: add FastAPI server for todo agent"
```

---

## Task 6: 添加测试

**Files:**
- Create: `todo-mcp/tests/test_agent.py`

**Step 1: 创建测试文件**

```python
# todo-mcp/tests/test_agent.py
"""Tests for todo agent."""
import pytest
from unittest.mock import Mock, patch


def test_get_all_tools():
    """测试获取所有工具。"""
    from todo_mcp.agent import get_all_tools

    tools = get_all_tools()
    assert len(tools) == 7

    tool_names = [t.name for t in tools]
    assert "add_task" in tool_names
    assert "get_today" in tool_names
    assert "suggest_schedule" in tool_names


def test_system_prompt():
    """测试系统提示词。"""
    from todo_mcp.agent import get_system_prompt

    prompt = get_system_prompt()
    assert "个人计划管理助手" in prompt
    assert "当前日期" in prompt


def test_session_manager():
    """测试会话管理器。"""
    from todo_mcp.agent import SessionManager

    manager = SessionManager()

    # 获取记忆
    memory1 = manager.get_memory("session1")
    assert memory1 is not None

    # 相同 session 返回相同 memory
    memory1_again = manager.get_memory("session1")
    assert memory1 is memory1_again

    # 不同 session 返回不同 memory
    memory2 = manager.get_memory("session2")
    assert memory1 is not memory2

    # 清除会话
    manager.clear_session("session1")
    memory1_new = manager.get_memory("session1")
    assert memory1 is not memory1_new


def test_add_task_tool():
    """测试添加任务工具。"""
    from todo_mcp.agent.tools import add_task

    # 工具应该可以被调用
    assert hasattr(add_task, 'name')
    assert add_task.name == "add_task"


def test_suggest_schedule_tool():
    """测试智能建议工具。"""
    from todo_mcp.agent.tools import suggest_schedule

    result = suggest_schedule.invoke({})
    assert "建议" in result or "暂无" in result
```

**Step 2: 运行测试**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_agent.py -v`
Expected: 所有测试通过

**Step 3: 提交**

```bash
git add tests/test_agent.py
git commit -m "test: add tests for todo agent"
```

---

## Task 7: 更新文档

**Files:**
- Modify: `todo-mcp/README.md`

**Step 1: 更新 README**

```markdown
# todo-mcp

个人计划管理智能助手，支持多轮对话和智能建议。

## 特性

- 🤖 智能对话交互
- 📅 任务管理（添加/查看/更新/删除）
- 📊 进度分析和健康状态评估
- 💡 智能安排建议
- 💻 支持命令行和 HTTP API

## 安装

```bash
cd todo-mcp
uv sync
```

## 配置

创建 `config.yaml` 文件:

```yaml
llm:
  base_url: http://localhost:11434/v1  # Ollama
  model: qwen2.5
  temperature: 0.7

todo_root: ~/todo
default_reminder_days: 3
```

## 使用

### 命令行对话

```bash
# 启动交互式对话
todo-agent chat

# 指定模型
todo-agent chat --model qwen2.5 --base-url http://localhost:11434/v1
```

### HTTP API

```bash
# 启动 API 服务
todo-agent serve --port 8080

# 调用 API
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "今天有什么任务？"}'
```

### MCP Server（兼容模式）

```bash
# STDIO 模式
uv run todo-mcp

# HTTP 模式
uv run todo-mcp --http --port 33333
```

## 示例对话

```
> 今天有什么任务？
📅 今日概览 (2026/3/10)
📊 统计: 总计 3 项任务, 已完成 1 项, 待办 2 项

> 帮我添加一个明天要完成的报告
已添加任务: 完成报告 到 明天

> 给我一些建议
💡 智能安排建议...
```

## 开发

```bash
# 运行测试
uv run pytest

# 运行 Agent
uv run todo-agent chat
```

## 许可证

MIT
```

**Step 2: 提交**

```bash
git add README.md
git commit -m "docs: update README for todo agent"
```

---

## 完成清单

- [ ] 依赖已添加
- [ ] Agent 工具已创建
- [ ] Agent 核心逻辑已实现
- [ ] CLI 接口已创建
- [ ] HTTP API 已创建
- [ ] 测试已添加
- [ ] 文档已更新
