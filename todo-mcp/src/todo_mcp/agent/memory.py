# todo-mcp/src/todo_mcp/agent/memory.py
"""Memory management for todo agent."""
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, List
import threading


class SimpleChatHistory:
    """简单的聊天历史管理类。"""

    def __init__(self):
        self._messages: List[BaseMessage] = []

    def add_message(self, message: BaseMessage) -> None:
        """添加消息。"""
        self._messages.append(message)

    def add_user_message(self, content: str) -> None:
        """添加用户消息。"""
        self._messages.append(HumanMessage(content=content))

    def add_ai_message(self, content: str) -> None:
        """添加 AI 消息。"""
        self._messages.append(AIMessage(content=content))

    @property
    def messages(self) -> List[BaseMessage]:
        """获取所有消息。"""
        return self._messages

    def clear(self) -> None:
        """清空历史。"""
        self._messages = []


class SessionManager:
    """管理多个会话的记忆。"""

    def __init__(self, max_sessions: int = 100):
        self._sessions: Dict[str, SimpleChatHistory] = {}
        self._lock = threading.Lock()
        self._max_sessions = max_sessions

    def get_memory(self, session_id: str) -> SimpleChatHistory:
        """获取或创建会话记忆。"""
        with self._lock:
            if session_id not in self._sessions:
                # 清理旧会话
                if len(self._sessions) >= self._max_sessions:
                    oldest = next(iter(self._sessions))
                    del self._sessions[oldest]

                self._sessions[session_id] = SimpleChatHistory()
            return self._sessions[session_id]

    def clear_session(self, session_id: str) -> None:
        """清除指定会话。"""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]

    def get_history(self, session_id: str) -> List[BaseMessage]:
        """获取会话历史。"""
        memory = self.get_memory(session_id)
        return memory.messages


# 全局会话管理器
session_manager = SessionManager()
