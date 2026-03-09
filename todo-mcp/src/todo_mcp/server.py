from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from typing import List


def create_server() -> Server:
    server = Server("todo-mcp")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name="add_task",
                description="添加任务到指定时间",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "任务内容"},
                        "time_expr": {"type": "string", "description": "时间表达，如'今天'、'本周'"},
                        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                        "due_date": {"type": "string", "description": "截止日期"}
                    },
                    "required": ["content", "time_expr"]
                }
            ),
            Tool(
                name="get_today",
                description="获取今日任务概览",
                inputSchema={"type": "object", "properties": {}}
            ),
            # 其他 tools 将在后续添加
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        # 占位实现
        return [TextContent(type="text", text=f"Tool {name} called with {arguments}")]

    return server


def main():
    import asyncio
    asyncio.run(stdio_server(create_server()))


if __name__ == "__main__":
    main()
