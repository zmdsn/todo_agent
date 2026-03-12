# tests/test_reader.py
import tempfile
from pathlib import Path
from todo_mcp.parser.reader import MarkdownReader

def test_read_tasks_from_month_file():
    content = """# March 月度计划

## 任务清单

### 第一周 (3/1 - 3/7)

#### 3/9 周日
- [ ] 完成报告
- [x] 提交代码
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()
        reader = MarkdownReader(Path(f.name))
        tasks = reader.read_tasks()

        assert len(tasks) == 2
        assert tasks[0].content == "完成报告"
        assert tasks[0].status.value == "pending"
        assert tasks[1].status.value == "completed"


def test_read_hierarchical_tasks():
    """测试读取层级任务"""
    content = """# March 月度计划

## 12日

- [ ] 完成报告 (预估: 4h)
  - [ ] 收集数据 (预估: 1h)
  - [ ] 撰写初稿 (预估: 2h)
  - [ ] 审核修改 (预估: 1h)
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()

        reader = MarkdownReader(Path(f.name))
        tasks = reader.read_tasks()

        # 找到父任务
        parent = next((t for t in tasks if "完成报告" in t.content), None)
        assert parent is not None
        assert parent.estimated_minutes == 240
        assert len(parent.subtask_ids) == 3

        # 检查子任务
        subtask = next((t for t in tasks if "收集数据" in t.content), None)
        assert subtask is not None
        assert subtask.parent_id == parent.id
        assert subtask.estimated_minutes == 60


def test_parse_estimated_time():
    """测试解析预估时间"""
    content = """# March

## 12日

- [ ] 任务1 (预估: 2h)
- [ ] 任务2 (预估: 30m)
- [ ] 任务3 (预估: 1.5h)
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()

        reader = MarkdownReader(Path(f.name))
        tasks = reader.read_tasks()

        assert tasks[0].estimated_minutes == 120
        assert tasks[1].estimated_minutes == 30
        assert tasks[2].estimated_minutes == 90
