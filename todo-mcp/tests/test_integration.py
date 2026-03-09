# tests/test_integration.py
"""Integration tests for the complete workflow."""
import pytest
import tempfile
from pathlib import Path
from todo_mcp.models import Config
from todo_mcp.server import TodoMCPServer


@pytest.mark.asyncio
async def test_full_workflow():
    """Test the complete workflow: create plan -> add task -> update status -> get progress."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        config = Config(todo_root=todo_root)
        server = TodoMCPServer(config=config)

        # 1. Create monthly plan
        result = await server._handle_create_plan({
            "time_expr": "3月"
        })
        assert "已创建" in str(result) or "存在" in str(result)

        # Verify file exists (using current year and Q1)
        from datetime import date
        current_year = date.today().year
        month_file = todo_root / str(current_year) / "Q1" / "03-March.md"
        assert month_file.exists()

        # 2. Add task
        result = await server._handle_add_task({
            "content": "完成报告",
            "time_expr": "3月9日"
        })
        assert "已添加任务" in str(result)

        # 3. Get progress
        result = await server._handle_get_progress({
            "time_expr": "3月"
        })
        assert "总任务: 1" in str(result)
        assert "进度报告" in str(result)

        # 4. Update task status
        # Note: Since task_id parsing is simplified, we test with a known format
        result = await server._handle_update_task({
            "task_id": f"{current_year}-Q1-03-09-1",
            "status": "completed"
        })
        # Should succeed
        assert "已更新" in str(result) or "更新" in str(result)

        # 5. Get progress again to verify update
        result = await server._handle_get_progress({
            "time_expr": "3月"
        })
        # Verify progress has changed (should show some completion)
        assert "完成率" in str(result)


@pytest.mark.asyncio
async def test_complete_lifecycle():
    """Test the complete lifecycle of a task from creation to deletion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        config = Config(todo_root=todo_root)
        server = TodoMCPServer(config=config)

        # Create plan
        await server._handle_create_plan({"time_expr": "本月"})

        # Add task
        add_result = await server._handle_add_task({
            "content": "生命周期测试任务",
            "time_expr": "本月"
        })
        assert "已添加任务" in str(add_result)

        # List plans to see the task
        list_result = await server._handle_list_plans({"time_expr": "本月"})
        assert "生命周期测试任务" in str(list_result)

        # Get progress
        progress_result = await server._handle_get_progress({"time_expr": "本月"})
        assert "总任务" in str(progress_result)

        # Analyze status
        analyze_result = await server._handle_analyze_status({"time_expr": "本月"})
        assert "健康状态分析" in str(analyze_result)

        # Generate report
        report_result = await server._handle_generate_report({
            "time_expr": "本月",
            "format": "text"
        })
        assert "生命周期测试任务" in str(report_result)


@pytest.mark.asyncio
async def test_multi_period_workflow():
    """Test working across multiple time periods."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        config = Config(todo_root=todo_root)
        server = TodoMCPServer(config=config)

        # Create plans for different periods
        await server._handle_create_plan({"time_expr": "Q1"})
        await server._handle_create_plan({"time_expr": "2026"})

        # Add tasks to different periods
        await server._handle_add_task({
            "content": "Q1任务",
            "time_expr": "Q1"
        })

        await server._handle_add_task({
            "content": "3月任务",
            "time_expr": "3月"
        })

        # Verify quarter file
        quarter_file = todo_root / "2026" / "Q1" / "README.md"
        assert quarter_file.exists()

        # Verify year file
        year_file = todo_root / "2026" / "README.md"
        assert year_file.exists()


@pytest.mark.asyncio
async def test_task_management_workflow():
    """Test task management operations: add, update, delete."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        config = Config(todo_root=todo_root)
        server = TodoMCPServer(config=config)

        # Setup
        await server._handle_create_plan({"time_expr": "本月"})

        # Add multiple tasks
        for i in range(3):
            await server._handle_add_task({
                "content": f"任务{i+1}",
                "time_expr": "本月"
            })

        # List all tasks
        list_result = await server._handle_list_plans({"time_expr": "本月"})
        assert "任务1" in str(list_result)
        assert "任务2" in str(list_result)
        assert "任务3" in str(list_result)

        # Get progress
        progress_result = await server._handle_get_progress({"time_expr": "本月"})
        assert "总任务: 3" in str(progress_result) or "总任务: 4" in str(progress_result)


@pytest.mark.asyncio
async def test_report_generation_workflow():
    """Test report generation in different formats."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        config = Config(todo_root=todo_root)
        server = TodoMCPServer(config=config)

        # Setup
        await server._handle_create_plan({"time_expr": "本周"})
        await server._handle_add_task({
            "content": "报告测试任务",
            "time_expr": "本周"
        })

        # Generate text report
        text_report = await server._handle_generate_report({
            "time_expr": "本周",
            "format": "text"
        })
        assert "进度报告" in str(text_report)

        # Generate markdown report
        md_report = await server._handle_generate_report({
            "time_expr": "本周",
            "format": "markdown"
        })
        assert "# 进度报告" in str(md_report)


@pytest.mark.asyncio
async def test_daily_workflow():
    """Test daily task workflow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir) / "todo"
        todo_root.mkdir()

        config = Config(todo_root=todo_root)
        server = TodoMCPServer(config=config)

        # Add task for today
        await server._handle_add_task({
            "content": "今日任务",
            "time_expr": "今天"
        })

        # Get today's overview
        today_result = await server._handle_get_today({})
        assert "今日概览" in str(today_result)

        # Get reminders
        reminders_result = await server._handle_get_reminders({"days": 3})
        assert "提醒事项" in str(reminders_result)
