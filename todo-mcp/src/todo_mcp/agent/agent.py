# todo-mcp/src/todo_mcp/agent/agent.py
"""LangChain agent for todo management."""
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Dict, Any, Optional

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
        Compiled StateGraph 实例
    """
    llm = ChatOpenAI(
        base_url=base_url,
        model=model,
        temperature=temperature,
        api_key=api_key
    )

    tools = get_all_tools()

    # 使用新的 create_agent API (LangGraph-based)
    graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt=get_system_prompt()
    )

    return graph


def run_agent(
    agent,
    message: str,
    session_manager: SessionManager,
    session_id: str = "default"
) -> str:
    """运行 Agent 并返回响应。

    Args:
        agent: Compiled StateGraph 实例
        message: 用户消息
        session_manager: 会话管理器
        session_id: 会话ID

    Returns:
        Agent 响应
    """
    from datetime import date

    memory = session_manager.get_memory(session_id)
    chat_history = memory.messages

    # 动态注入当前日期（因为 agent 创建时日期被缓存了）
    today = date.today()
    date_context = f"[系统提示: 当前日期是 {today.year}年{today.month}月{today.day}日，请以此为准。]\n\n"

    # 构建消息列表，在用户消息前添加日期上下文
    messages = list(chat_history) + [HumanMessage(content=date_context + message)]

    # 调用 agent
    result = agent.invoke({"messages": messages})

    # 提取最后一条 AI 消息作为响应
    output = ""
    if result and "messages" in result:
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage):
                output = msg.content
                break

    # 保存到记忆（保存原始用户消息，不包含日期上下文）
    memory.add_user_message(message)
    memory.add_ai_message(output)

    return output
