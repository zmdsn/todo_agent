# tests/test_writer.py
import tempfile
from pathlib import Path
from todo_mcp.parser.writer import MarkdownWriter
from todo_mcp.parser.reader import MarkdownReader
from todo_mcp.models import Task, TaskStatus


def test_add_task_to_file():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# March 月度计划\n\n## 任务清单\n\n### 第一周\n\n#### 3/9 周日\n")
        f.flush()

        writer = MarkdownWriter(Path(f.name))
        task = Task(
            id="2026-Q1-03-09-1",
            content="新任务",
            status=TaskStatus.PENDING,
            location=f.name
        )
        writer.add_task(task, day=9)

        reader = MarkdownReader(Path(f.name))
        tasks = reader.read_tasks()
        assert any(t.content == "新任务" for t in tasks)


def test_update_task_status():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# March\n\n#### 3/9\n- [ ] 完成报告\n")
        f.flush()

        writer = MarkdownWriter(Path(f.name))
        writer.update_task_status("2026-Q1-03-09-1", TaskStatus.COMPLETED)

        content = Path(f.name).read_text()
        assert "- [x] 完成报告" in content
