import pytest
from mcp.types import ListToolsRequest
from todo_mcp.server import create_server


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
