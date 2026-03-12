import pytest
import tempfile
from pathlib import Path
from datetime import date
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
    assert "update_task" in tool_names
    assert "get_progress" in tool_names
    assert "list_plans" in tool_names
    assert "create_plan" in tool_names
    assert "delete_task" in tool_names
    assert "move_task" in tool_names
    assert "get_reminders" in tool_names
    assert "analyze_status" in tool_names
    assert "generate_report" in tool_names


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


@pytest.mark.asyncio
async def test_get_today_empty():
    """Test get_today with no tasks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        server = TodoMCPServer(config=Config(todo_root=todo_root))
        result = await server._handle_get_today({})

        assert "今日概览" in str(result)
        assert "暂无任务" in str(result)


@pytest.mark.asyncio
async def test_get_today_with_tasks():
    """Test get_today with existing tasks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        server = TodoMCPServer(config=Config(todo_root=todo_root))

        # First add a task for today
        await server._handle_add_task({
            "content": "今日测试任务",
            "time_expr": "今天"
        })

        # Then get today's overview
        result = await server._handle_get_today({})

        assert "今日概览" in str(result)
        assert "今日测试任务" in str(result)


@pytest.mark.asyncio
async def test_get_progress():
    """Test get_progress tool."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        server = TodoMCPServer(config=Config(todo_root=todo_root))

        # Add some tasks
        await server._handle_add_task({
            "content": "任务1",
            "time_expr": "本月"
        })

        result = await server._handle_get_progress({"time_expr": "本月"})

        assert "进度报告" in str(result)
        assert "完成率" in str(result)


@pytest.mark.asyncio
async def test_list_plans():
    """Test list_plans tool."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        server = TodoMCPServer(config=Config(todo_root=todo_root))

        # Add some tasks
        await server._handle_add_task({
            "content": "计划任务1",
            "time_expr": "本月"
        })

        result = await server._handle_list_plans({"time_expr": "本月"})

        assert "计划列表" in str(result)
        assert "计划任务1" in str(result)


@pytest.mark.asyncio
async def test_create_plan():
    """Test create_plan tool."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        server = TodoMCPServer(config=Config(todo_root=todo_root))

        result = await server._handle_create_plan({
            "time_expr": "本月"
        })

        assert "已创建计划文件" in str(result)


@pytest.mark.asyncio
async def test_create_plan_already_exists():
    """Test create_plan when file already exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        server = TodoMCPServer(config=Config(todo_root=todo_root))

        # Create plan first time
        await server._handle_create_plan({"time_expr": "本月"})

        # Try to create again
        result = await server._handle_create_plan({"time_expr": "本月"})

        assert "已存在" in str(result)


@pytest.mark.asyncio
async def test_update_task_missing_id():
    """Test update_task without task_id."""
    server = TodoMCPServer()
    result = await server._handle_update_task({})

    assert "错误" in str(result)
    assert "task_id" in str(result)


@pytest.mark.asyncio
async def test_delete_task_missing_id():
    """Test delete_task without task_id."""
    server = TodoMCPServer()
    result = await server._handle_delete_task({})

    assert "错误" in str(result)


@pytest.mark.asyncio
async def test_move_task_missing_params():
    """Test move_task without required params."""
    server = TodoMCPServer()
    result = await server._handle_move_task({})

    assert "错误" in str(result)


@pytest.mark.asyncio
async def test_get_reminders():
    """Test get_reminders tool."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        server = TodoMCPServer(config=Config(todo_root=todo_root))

        result = await server._handle_get_reminders({"days": 3})

        assert "提醒事项" in str(result)


@pytest.mark.asyncio
async def test_analyze_status():
    """Test analyze_status tool."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        server = TodoMCPServer(config=Config(todo_root=todo_root))

        # Add some tasks first
        await server._handle_add_task({
            "content": "分析测试任务",
            "time_expr": "本月"
        })

        result = await server._handle_analyze_status({"time_expr": "本月"})

        assert "健康状态分析" in str(result)
        assert "健康度" in str(result)


@pytest.mark.asyncio
async def test_generate_report_text():
    """Test generate_report tool with text format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        server = TodoMCPServer(config=Config(todo_root=todo_root))

        # Add some tasks first
        await server._handle_add_task({
            "content": "报告测试任务",
            "time_expr": "本周"
        })

        result = await server._handle_generate_report({
            "time_expr": "本周",
            "format": "text"
        })

        assert "进度报告" in str(result)
        assert "统计概览" in str(result)


@pytest.mark.asyncio
async def test_generate_report_markdown():
    """Test generate_report tool with markdown format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        server = TodoMCPServer(config=Config(todo_root=todo_root))

        # Add some tasks first
        await server._handle_add_task({
            "content": "Markdown报告任务",
            "time_expr": "本周"
        })

        result = await server._handle_generate_report({
            "time_expr": "本周",
            "format": "markdown"
        })

        assert "# 进度报告" in str(result)
        assert "## 概览" in str(result)
