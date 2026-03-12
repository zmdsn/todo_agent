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


def test_config_task_split_defaults():
    """测试任务拆分配置默认值"""
    config = Config()
    assert config.task_split_threshold_minutes == 120
    assert config.task_split_target_minutes == 60
    assert config.auto_complete_parent == True


def test_task_with_parent():
    """测试带父任务的任务"""
    task = Task(
        id="2026-Q1-03-12-1-1",
        content="收集数据",
        status=TaskStatus.PENDING,
        location="2026/Q1/03-March.md",
        parent_id="2026-Q1-03-12-1"
    )
    assert task.parent_id == "2026-Q1-03-12-1"


def test_task_with_estimated_time():
    """测试带预估时间的任务"""
    task = Task(
        id="2026-Q1-03-12-1",
        content="完成报告",
        status=TaskStatus.PENDING,
        location="2026/Q1/03-March.md",
        estimated_minutes=120
    )
    assert task.estimated_minutes == 120


def test_task_with_subtasks():
    """测试带子任务列表的任务"""
    task = Task(
        id="2026-Q1-03-12-1",
        content="完成报告",
        status=TaskStatus.PENDING,
        location="2026/Q1/03-March.md",
        subtask_ids=["2026-Q1-03-12-1-1", "2026-Q1-03-12-1-2"]
    )
    assert len(task.subtask_ids) == 2
