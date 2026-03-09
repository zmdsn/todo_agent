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
