from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from typing import List, Optional
from pathlib import Path
import uuid

from todo_mcp.models import Task, TaskStatus, Config
from todo_mcp.utils.time import TimeParser
from todo_mcp.parser.writer import MarkdownWriter


class TodoMCPServer:
    """Todo MCP Server implementation."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self._task_counter = 0

    def _generate_task_id(self, year: int, quarter: int, month: int, day: Optional[int] = None) -> str:
        """Generate a unique task ID."""
        self._task_counter += 1
        day_part = f"-{day}" if day else ""
        return f"{year}-{quarter}-{month}{day_part}-{self._task_counter}"

    async def _handle_add_task(self, arguments: dict) -> List[TextContent]:
        """Handle add_task tool call."""
        content = arguments["content"]
        time_expr = arguments["time_expr"]
        priority = arguments.get("priority")
        due_date = arguments.get("due_date")

        # Parse time expression
        parser = TimeParser()
        parsed = parser.parse(time_expr)

        # Get file path (remove anchor if present)
        file_path_str = parsed.to_file_path()
        if "#" in file_path_str:
            file_path_str = file_path_str.split("#")[0]
        file_path = self.config.todo_root / file_path_str

        # Ensure file exists
        writer = MarkdownWriter(file_path)
        if not file_path.exists():
            writer.ensure_file_exists(parsed.year, parsed.quarter, parsed.month)

        # Create task
        task = Task(
            id=self._generate_task_id(
                parsed.year, parsed.quarter, parsed.month, parsed.day
            ),
            content=content,
            status=TaskStatus.PENDING,
            location=str(file_path),
            priority=priority,
            due_date=due_date
        )

        # Add task to file
        writer.add_task(task, day=parsed.day)

        return [TextContent(type="text", text=f"已添加任务: {content} 到 {time_expr}")]


def create_server(config: Optional[Config] = None) -> Server:
    """Create the MCP server instance."""
    server = Server("todo-mcp")
    todo_server = TodoMCPServer(config)

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
        if name == "add_task":
            return await todo_server._handle_add_task(arguments)
        # Placeholder for other tools
        return [TextContent(type="text", text=f"Tool {name} called with {arguments}")]

    return server


def main():
    import asyncio
    asyncio.run(stdio_server(create_server()))


if __name__ == "__main__":
    main()
