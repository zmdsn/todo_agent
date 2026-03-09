from todo_mcp.models.task import Task, TaskStatus
from todo_mcp.models.config import Config


def test_task_creation():
    task = Task(
        id="2026-Q1-03-09-1",
        content="完成报告",
        status=TaskStatus.PENDING,
        location="2026/Q1/03-March.md"
    )
    assert task.id == "2026-Q1-03-09-1"
    assert task.status == TaskStatus.PENDING


def test_config_defaults():
    config = Config()
    assert config.todo_root.name == "todo"
    assert config.default_reminder_days == 3
