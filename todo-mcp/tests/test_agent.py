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
