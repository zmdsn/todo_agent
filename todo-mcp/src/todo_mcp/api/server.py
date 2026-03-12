# todo-mcp/src/todo_mcp/api/server.py
"""FastAPI server for todo agent."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid

from todo_mcp.agent import create_todo_agent, run_agent, session_manager
from todo_mcp.reminder import ReminderChecker
from todo_mcp.reminder.engine import ReminderEngine
from todo_mcp.reminder.rules import RuleManager
from todo_mcp.reminder.scheduler import ReminderScheduler
from todo_mcp.reminder.config import load_reminder_config
from todo_mcp.reminder.notifiers.cli import CliNotifier


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

    @app.on_event("startup")
    async def startup_reminder():
        """Initialize reminder system on startup."""
        config = load_reminder_config("config.yaml")

        if not config.enabled:
            return

        rule_manager = RuleManager(rules=config.rules)
        checker = ReminderChecker()
        notifiers = {}

        # Setup CLI notifier
        cli_config = config.channels.get("cli", {})
        if cli_config.get("enabled", False):
            notifiers["cli"] = CliNotifier(
                enabled=True,
                sound=cli_config.get("sound", False),
            )

        engine = ReminderEngine(
            rule_manager=rule_manager,
            checker=checker,
            notifiers=notifiers,
        )

        scheduler = ReminderScheduler(engine=engine)
        # Start scheduler as background task (don't await)
        import asyncio
        asyncio.create_task(scheduler._run_monitor())
        asyncio.create_task(scheduler._run_scheduled())

        app.state.reminder_engine = engine
        app.state.reminder_scheduler = scheduler

    @app.on_event("shutdown")
    async def shutdown_reminder():
        """Cleanup reminder system on shutdown."""
        scheduler = getattr(app.state, "reminder_scheduler", None)
        if scheduler:
            await scheduler.stop()

    return app


# 用于 uvicorn 直接运行
app = create_app()
