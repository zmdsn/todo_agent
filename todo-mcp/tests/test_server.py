import pytest
import tempfile
from pathlib import Path
from mcp.types import ListToolsRequest
from todo_mcp.server import create_server, TodoMCPServer
from todo_mcp.models import Config


@pytest.mark.asyncio
async def test_server_creation():
    server = create_server()
    assert server.name == "todo-mcp"


@pytest.mark.asyncio
async def test_list_tools():
    server = create_server()
    # Get the list tools handler
    handler = server.request_handlers[ListToolsRequest]
    # Call the handler to get the tools
    result = await handler(ListToolsRequest())
    # Extract tool names from the result (result is ServerResult, root is ListToolsResult)
    tool_names = [t.name for t in result.root.tools]
    assert "add_task" in tool_names
    assert "get_today" in tool_names


@pytest.mark.asyncio
async def test_add_task_tool():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create simulated todo directory structure
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        # Test adding task
        server = TodoMCPServer(config=Config(todo_root=todo_root))
        result = await server._handle_add_task({
            "content": "测试任务",
            "time_expr": "今天"
        })

        # Verify result
        assert "测试任务" in str(result)
        assert "已添加任务" in str(result)
