# 任务拆分与时间预估实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 todo-mcp 添加智能任务拆分和时间预估功能

**Architecture:** 扩展 Task 模型支持父子关系和预估时间，修改 Reader/Writer 支持层级任务解析，新增 estimate_task/split_task 工具，通过 LLM 驱动任务分析。

**Tech Stack:** Python, Pydantic, LangChain, pytest

---

## Task 1: 扩展 Task 模型

**Files:**
- Modify: `todo-mcp/src/todo_mcp/models/task.py`
- Modify: `todo-mcp/tests/test_models.py`

**Step 1: 编写失败的测试**

```python
# 添加到 tests/test_models.py

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
```

**Step 2: 运行测试确认失败**

Run: `cd todo-mcp && uv run pytest tests/test_models.py -v`
Expected: FAIL - 字段不存在

**Step 3: 扩展 Task 模型**

```python
# 修改 todo-mcp/src/todo_mcp/models/task.py

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List


class TaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class Task(BaseModel):
    id: str = Field(..., description="唯一标识，格式: {年}-{季}-{月}-{日}-{序号}")
    content: str = Field(..., description="任务内容")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    location: str = Field(..., description="文件路径")
    due_date: Optional[str] = Field(None, description="截止日期")
    priority: Optional[str] = Field(None, description="优先级: high/medium/low")

    # 新增字段
    parent_id: Optional[str] = Field(None, description="父任务ID")
    estimated_minutes: Optional[int] = Field(None, description="预估时间（分钟）")
    subtask_ids: List[str] = Field(default_factory=list, description="子任务ID列表")
```

**Step 4: 运行测试确认通过**

Run: `cd todo-mcp && uv run pytest tests/test_models.py -v`
Expected: PASS

**Step 5: 提交**

```bash
git add todo-mcp/src/todo_mcp/models/task.py todo-mcp/tests/test_models.py
git commit -m "feat(models): add parent_id, estimated_minutes, subtask_ids to Task"
```

---

## Task 2: 扩展配置模型

**Files:**
- Modify: `todo-mcp/src/todo_mcp/models/config.py`
- Modify: `todo-mcp/tests/test_models.py`

**Step 1: 编写失败的测试**

```python
# 添加到 tests/test_models.py

def test_config_task_split_defaults():
    """测试任务拆分配置默认值"""
    config = Config()
    assert config.task_split_threshold_minutes == 120
    assert config.task_split_target_minutes == 60
    assert config.auto_complete_parent == True
```

**Step 2: 运行测试确认失败**

Run: `cd todo-mcp && uv run pytest tests/test_models.py::test_config_task_split_defaults -v`
Expected: FAIL

**Step 3: 扩展 Config 模型**

```python
# 修改 todo-mcp/src/todo_mcp/models/config.py

from pathlib import Path
from pydantic import BaseModel, Field


class Config(BaseModel):
    todo_root: Path = Field(
        default_factory=lambda: Path.home() / "todo",
        description="计划文件根目录"
    )
    default_reminder_days: int = Field(
        default=3,
        description="默认提前提醒天数"
    )

    # 任务拆分配置
    task_split_threshold_minutes: int = Field(
        default=120,
        description="超过此时间（分钟）提示拆分"
    )
    task_split_target_minutes: int = Field(
        default=60,
        description="子任务目标时长（分钟）"
    )
    auto_complete_parent: bool = Field(
        default=True,
        description="子任务全完成时自动完成父任务"
    )
```

**Step 4: 运行测试确认通过**

Run: `cd todo-mcp && uv run pytest tests/test_models.py::test_config_task_split_defaults -v`
Expected: PASS

**Step 5: 提交**

```bash
git add todo-mcp/src/todo_mcp/models/config.py todo-mcp/tests/test_models.py
git commit -m "feat(config): add task split configuration options"
```

---

## Task 3: 扩展 MarkdownReader 支持层级任务

**Files:**
- Modify: `todo-mcp/src/todo_mcp/parser/reader.py`
- Modify: `todo-mcp/tests/test_reader.py`

**Step 1: 编写失败的测试**

```python
# 添加到 tests/test_reader.py

import tempfile
from pathlib import Path
from todo_mcp.parser.reader import MarkdownReader


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
```

**Step 2: 运行测试确认失败**

Run: `cd todo-mcp && uv run pytest tests/test_reader.py::test_read_hierarchical_tasks tests/test_reader.py::test_parse_estimated_time -v`
Expected: FAIL

**Step 3: 实现 MarkdownReader 扩展**

```python
# 修改 todo-mcp/src/todo_mcp/parser/reader.py

from pathlib import Path
import re
from typing import List, Optional
from todo_mcp.models import Task, TaskStatus


class MarkdownReader:
    TASK_PATTERN = re.compile(r"^(\s*)(-|\*)\s+\[([ xX])\]\s+(.+)$", re.MULTILINE)
    DAY_PATTERN = re.compile(r"^#+\s+(\d{1,2})/(\d{1,2})", re.MULTILINE)
    DAY_CN_PATTERN = re.compile(r"^#+\s+(\d{1,2})[日号]", re.MULTILINE)
    ESTIMATE_PATTERN = re.compile(r"\(预估:\s*([\d.]+)\s*([hm])\)")

    def __init__(self, file_path: Path):
        self.file_path = file_path

    def _parse_day_header(self, line: str) -> Optional[int]:
        """Parse day from header line, supporting multiple formats."""
        day_match = self.DAY_PATTERN.match(line.strip())
        if day_match:
            return int(day_match.group(2))

        cn_match = self.DAY_CN_PATTERN.match(line.strip())
        if cn_match:
            return int(cn_match.group(1))

        return None

    def _parse_estimated_minutes(self, content: str) -> Optional[int]:
        """解析预估时间"""
        match = self.ESTIMATE_PATTERN.search(content)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            if unit == 'h':
                return int(value * 60)
            else:
                return int(value)
        return None

    def _clean_content(self, content: str) -> str:
        """移除预估时间标记，返回纯任务内容"""
        return self.ESTIMATE_PATTERN.sub('', content).strip()

    def _count_indent(self, indent: str) -> int:
        """计算缩进层级（2空格=1层）"""
        return len(indent) // 2

    def read_tasks(self) -> List[Task]:
        if not self.file_path.exists():
            return []

        content = self.file_path.read_text(encoding='utf-8')
        tasks = []
        current_day = None
        task_counter = 0

        # 用于跟踪父任务
        indent_stack = []  # [(indent_level, task)]

        lines = content.split('\n')
        for line in lines:
            # 检查日期标题
            day = self._parse_day_header(line.strip())
            if day is not None:
                current_day = day
                task_counter = 0
                indent_stack = []
                continue

            # 检查任务
            task_match = self.TASK_PATTERN.match(line)
            if task_match:
                indent_str = task_match.group(1)
                status_char = task_match.group(3)
                raw_content = task_match.group(4).strip()

                task_counter += 1
                status = TaskStatus.COMPLETED if status_char.lower() == 'x' else TaskStatus.PENDING
                estimated_minutes = self._parse_estimated_minutes(raw_content)
                clean_content = self._clean_content(raw_content)
                indent_level = self._count_indent(indent_str)

                task_id = self._generate_task_id(current_day, task_counter)
                parent_id = None

                # 处理层级关系
                while indent_stack and indent_stack[-1][0] >= indent_level:
                    indent_stack.pop()

                if indent_stack:
                    parent_id = indent_stack[-1][1].id
                    indent_stack[-1][1].subtask_ids.append(task_id)

                task = Task(
                    id=task_id,
                    content=clean_content,
                    status=status,
                    location=str(self.file_path),
                    estimated_minutes=estimated_minutes,
                    parent_id=parent_id
                )
                tasks.append(task)

                # 将当前任务加入栈，作为后续子任务的父任务
                indent_stack.append((indent_level, task))

        return tasks

    def _generate_task_id(self, day: int, counter: int) -> str:
        parts = self.file_path.parts
        year = parts[-3] if len(parts) >= 3 else "2026"
        quarter = parts[-2].replace("Q", "") if len(parts) >= 2 else "1"
        month_file = parts[-1].replace(".md", "")
        month = month_file.split("-")[0]

        day_str = f"{day:02d}" if day else "00"
        return f"{year}-Q{quarter}-{month}-{day_str}-{counter}"
```

**Step 4: 运行测试确认通过**

Run: `cd todo-mcp && uv run pytest tests/test_reader.py -v`
Expected: PASS

**Step 5: 提交**

```bash
git add todo-mcp/src/todo_mcp/parser/reader.py todo-mcp/tests/test_reader.py
git commit -m "feat(reader): support hierarchical tasks and estimated time parsing"
```

---

## Task 4: 扩展 MarkdownWriter 支持层级任务

**Files:**
- Modify: `todo-mcp/src/todo_mcp/parser/writer.py`
- Modify: `todo-mcp/tests/test_writer.py`

**Step 1: 编写失败的测试**

```python
# 添加到 tests/test_writer.py

import tempfile
from pathlib import Path
from todo_mcp.parser.writer import MarkdownWriter
from todo_mcp.models import Task, TaskStatus


def test_add_task_with_estimate():
    """测试添加带预估时间的任务"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# March\n\n## 12日\n")
        f.flush()

        writer = MarkdownWriter(Path(f.name))
        task = Task(
            id="2026-Q1-03-12-1",
            content="完成报告",
            status=TaskStatus.PENDING,
            location=f.name,
            estimated_minutes=240
        )
        writer.add_task(task, day=12)

        content = Path(f.name).read_text(encoding='utf-8')
        assert "(预估: 4h)" in content


def test_add_subtask():
    """测试添加子任务"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# March\n\n## 12日\n\n- [ ] 完成报告 (预估: 4h)\n")
        f.flush()

        writer = MarkdownWriter(Path(f.name))
        subtask = Task(
            id="2026-Q1-03-12-1-1",
            content="收集数据",
            status=TaskStatus.PENDING,
            location=f.name,
            parent_id="2026-Q1-03-12-1",
            estimated_minutes=60
        )
        writer.add_subtask(subtask, parent_line="完成报告")

        content = Path(f.name).read_text(encoding='utf-8')
        assert "  - [ ] 收集数据 (预估: 1h)" in content
```

**Step 2: 运行测试确认失败**

Run: `cd todo-mcp && uv run pytest tests/test_writer.py::test_add_task_with_estimate tests/test_writer.py::test_add_subtask -v`
Expected: FAIL

**Step 3: 实现 MarkdownWriter 扩展**

```python
# 修改 todo-mcp/src/todo_mcp/parser/writer.py

from pathlib import Path
import re
from typing import Optional, List
from todo_mcp.models import Task, TaskStatus


class MarkdownWriter:
    def __init__(self, file_path: Path):
        self.file_path = file_path

    def ensure_file_exists(self, year: int, quarter: int, month: int):
        """确保文件存在，不存在则创建模板"""
        if not self.file_path.exists():
            self._create_month_template(year, quarter, month)

    def _create_month_template(self, year: int, quarter: int, month: int):
        month_names = ["January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]
        content = f"# {month_names[month-1]} 月度计划\n\n"
        content += f"> {year}年{month}月\n\n"
        content += "## 本月重点\n\n1. [重点1]\n\n"
        content += "## 任务清单\n\n"
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(content, encoding='utf-8')

    def _format_task_line(self, task: Task, indent: int = 0) -> str:
        """格式化任务行"""
        indent_str = "  " * indent
        status_str = "[x]" if task.status == TaskStatus.COMPLETED else "[ ]"

        # 添加预估时间
        estimate_str = ""
        if task.estimated_minutes:
            hours = task.estimated_minutes / 60
            if hours >= 1:
                estimate_str = f" (预估: {hours:.0f}h)" if hours == int(hours) else f" (预估: {hours:.1f}h)"
            else:
                estimate_str = f" (预估: {task.estimated_minutes}m)"

        return f"{indent_str}- {status_str} {task.content}{estimate_str}\n"

    def add_task(self, task: Task, day: Optional[int] = None):
        """添加任务到文件"""
        content = self.file_path.read_text(encoding='utf-8') if self.file_path.exists() else ""

        task_line = self._format_task_line(task)

        if day:
            day_section = f"## {day}日"

            if day_section in content:
                content = content.replace(day_section, f"{day_section}\n{task_line}")
            else:
                content += f"\n{day_section}\n{task_line}"
        else:
            content += task_line

        self.file_path.write_text(content, encoding='utf-8')

    def add_subtask(self, subtask: Task, parent_content: str):
        """添加子任务到指定父任务下"""
        if not self.file_path.exists():
            return

        content = self.file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        for i, line in enumerate(lines):
            if parent_content in line and line.strip().startswith("-"):
                # 找到父任务，在其后插入子任务
                subtask_line = self._format_task_line(subtask, indent=1)
                lines.insert(i + 1, subtask_line.rstrip('\n'))
                break

        self.file_path.write_text('\n'.join(lines), encoding='utf-8')

    def add_subtasks(self, parent_task: Task, subtasks: List[Task]):
        """批量添加子任务"""
        for subtask in subtasks:
            self.add_subtask(subtask, parent_task.content)

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """更新任务状态"""
        if not self.file_path.exists():
            return False

        content = self.file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        for i, line in enumerate(lines):
            if re.match(r'^(\s*)(-|\*)\s+\[[ xX]\]', line):
                if status == TaskStatus.COMPLETED:
                    lines[i] = re.sub(r'\[ \]', '[x]', line)
                else:
                    lines[i] = re.sub(r'\[x\]', '[ ]', line, flags=re.IGNORECASE)
                break

        self.file_path.write_text('\n'.join(lines), encoding='utf-8')
        return True

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if not self.file_path.exists():
            return False

        content = self.file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        new_lines = []
        task_counter = 0

        for line in lines:
            if re.match(r'^(\s*)(-|\*)\s+\[[ xX]\]', line):
                task_counter += 1
                if task_counter == 1:
                    continue
            new_lines.append(line)

        self.file_path.write_text('\n'.join(new_lines), encoding='utf-8')
        return True
```

**Step 4: 运行测试确认通过**

Run: `cd todo-mcp && uv run pytest tests/test_writer.py -v`
Expected: PASS

**Step 5: 提交**

```bash
git add todo-mcp/src/todo_mcp/parser/writer.py todo-mcp/tests/test_writer.py
git commit -m "feat(writer): support hierarchical tasks and estimated time writing"
```

---

## Task 5: 创建时间预估工具

**Files:**
- Create: `todo-mcp/src/todo_mcp/utils/estimator.py`
- Create: `todo-mcp/tests/test_estimator.py`

**Step 1: 编写失败的测试**

```python
# 创建 tests/test_estimator.py

from todo_mcp.utils.estimator import TaskEstimator


def test_estimate_simple_task():
    """测试简单任务预估"""
    estimator = TaskEstimator()
    result = estimator.estimate("回复邮件")

    assert result["estimated_minutes"] > 0
    assert result["should_split"] == False


def test_estimate_complex_task():
    """测试复杂任务预估"""
    estimator = TaskEstimator()
    result = estimator.estimate("完成季度报告，包括数据收集、分析和撰写")

    assert result["estimated_minutes"] > 120
    assert result["should_split"] == True


def test_estimate_with_priority():
    """测试优先级影响预估"""
    estimator = TaskEstimator()

    low_result = estimator.estimate("写代码", priority="low")
    high_result = estimator.estimate("写代码", priority="high")

    # 高优先级任务预估时间应该更长
    assert high_result["estimated_minutes"] > low_result["estimated_minutes"]


def test_split_task():
    """测试任务拆分"""
    estimator = TaskEstimator()
    result = estimator.split("完成季度报告", target_minutes=60)

    assert len(result["subtasks"]) >= 2
    assert all(s["estimated_minutes"] <= 90 for s in result["subtasks"])
    assert result["total_minutes"] > 0
```

**Step 2: 运行测试确认失败**

Run: `cd todo-mcp && uv run pytest tests/test_estimator.py -v`
Expected: FAIL - 模块不存在

**Step 3: 创建时间预估器**

```python
# 创建 todo-mcp/src/todo_mcp/utils/estimator.py

from typing import Dict, List, Optional


class TaskEstimator:
    """任务时间预估器（基于规则，后续可接入 LLM）"""

    # 任务类型关键词 -> 基础时间（分钟）
    TASK_KEYWORDS = {
        # 沟通类
        "回复": 15,
        "邮件": 10,
        "电话": 20,
        "会议": 60,
        "沟通": 30,

        # 文档类
        "写": 45,
        "撰写": 60,
        "整理": 30,
        "总结": 45,
        "报告": 90,
        "文档": 60,

        # 开发类
        "开发": 120,
        "实现": 90,
        "修复": 45,
        "调试": 60,
        "代码": 60,
        "测试": 45,

        # 分析类
        "分析": 60,
        "研究": 90,
        "调研": 60,
        "评估": 45,

        # 学习类
        "学习": 60,
        "阅读": 30,
        "复习": 45,
    }

    # 复杂度修饰词
    COMPLEXITY_MODIFIERS = {
        "简单": 0.5,
        "快速": 0.5,
        "小": 0.7,
        "大": 1.5,
        "复杂": 1.5,
        "完整": 1.3,
        "详细": 1.3,
    }

    # 优先级系数
    PRIORITY_MULTIPLIERS = {
        "high": 1.2,
        "medium": 1.0,
        "low": 0.8,
    }

    def __init__(self, threshold_minutes: int = 120, target_minutes: int = 60):
        self.threshold_minutes = threshold_minutes
        self.target_minutes = target_minutes

    def estimate(self, content: str, priority: Optional[str] = None) -> Dict:
        """预估任务时间"""
        base_minutes = self._calculate_base_time(content)
        final_minutes = self._apply_priority(base_minutes, priority)

        return {
            "estimated_minutes": final_minutes,
            "should_split": final_minutes > self.threshold_minutes,
            "reason": f"预估时间 {final_minutes} 分钟" + (
                f"，超过 {self.threshold_minutes} 分钟阈值" if final_minutes > self.threshold_minutes else ""
            )
        }

    def _calculate_base_time(self, content: str) -> int:
        """计算基础时间"""
        content_lower = content.lower()
        total_minutes = 30  # 默认 30 分钟

        # 匹配关键词
        for keyword, minutes in self.TASK_KEYWORDS.items():
            if keyword in content:
                total_minutes = max(total_minutes, minutes)

        # 应用复杂度修饰
        for modifier, multiplier in self.COMPLEXITY_MODIFIERS.items():
            if modifier in content:
                total_minutes = int(total_minutes * multiplier)

        # 多步骤任务（包含"和"、"、"、"，"等）增加时间
        step_count = content.count("和") + content.count("、") + content.count("，") + 1
        if step_count > 1:
            total_minutes = int(total_minutes * (1 + (step_count - 1) * 0.3))

        return total_minutes

    def _apply_priority(self, minutes: int, priority: Optional[str]) -> int:
        """应用优先级调整"""
        if priority and priority in self.PRIORITY_MULTIPLIERS:
            return int(minutes * self.PRIORITY_MULTIPLIERS[priority])
        return minutes

    def split(self, content: str, priority: Optional[str] = None, target_minutes: int = None) -> Dict:
        """拆分任务为子任务"""
        if target_minutes is None:
            target_minutes = self.target_minutes

        estimate_result = self.estimate(content, priority)
        total_minutes = estimate_result["estimated_minutes"]

        # 如果不需要拆分，返回原任务
        if total_minutes <= self.threshold_minutes:
            return {
                "subtasks": [{"content": content, "estimated_minutes": total_minutes}],
                "total_minutes": total_minutes,
                "needs_split": False
            }

        # 生成子任务
        subtasks = self._generate_subtasks(content, total_minutes, target_minutes)

        return {
            "subtasks": subtasks,
            "total_minutes": total_minutes,
            "needs_split": True
        }

    def _generate_subtasks(self, content: str, total_minutes: int, target_minutes: int) -> List[Dict]:
        """生成子任务列表"""
        # 常见任务的拆分模板
        templates = {
            "报告": ["收集数据", "整理分析", "撰写初稿", "审核修改"],
            "开发": ["需求分析", "设计方案", "编码实现", "测试验证"],
            "文档": ["收集资料", "撰写内容", "审核修改"],
            "研究": ["收集信息", "分析整理", "总结输出"],
            "会议": ["准备材料", "参加会议", "整理纪要"],
        }

        # 匹配模板
        subtask_names = None
        for keyword, names in templates.items():
            if keyword in content:
                subtask_names = names
                break

        # 默认拆分
        if not subtask_names:
            num_subtasks = max(2, (total_minutes + target_minutes - 1) // target_minutes)
            subtask_names = [f"步骤{i+1}" for i in range(num_subtasks)]

        # 分配时间
        subtask_minutes = total_minutes // len(subtask_names)
        subtasks = []
        for name in subtask_names:
            subtasks.append({
                "content": f"{content[:10]}... - {name}" if len(content) > 10 else f"{content} - {name}",
                "estimated_minutes": subtask_minutes
            })

        # 调整最后一个子任务的时间
        if subtasks:
            subtasks[-1]["estimated_minutes"] += total_minutes % len(subtask_names)

        return subtasks
```

**Step 4: 运行测试确认通过**

Run: `cd todo-mcp && uv run pytest tests/test_estimator.py -v`
Expected: PASS

**Step 5: 提交**

```bash
git add todo-mcp/src/todo_mcp/utils/estimator.py todo-mcp/tests/test_estimator.py
git commit -m "feat(estimator): add task time estimation and splitting logic"
```

---

## Task 6: 添加 Agent 工具

**Files:**
- Modify: `todo-mcp/src/todo_mcp/agent/tools.py`
- Modify: `todo-mcp/tests/test_agent.py`

**Step 1: 编写失败的测试**

```python
# 添加到 tests/test_agent.py

from todo_mcp.agent.tools import estimate_task, split_task, add_task_with_split


def test_estimate_task_tool():
    """测试预估任务工具"""
    result = estimate_task.invoke({"content": "完成季度报告", "priority": "high"})
    assert "estimated_minutes" in result
    assert result["should_split"] == True


def test_split_task_tool():
    """测试拆分任务工具"""
    result = split_task.invoke({
        "content": "完成季度报告",
        "priority": "high",
        "target_minutes": 60
    })
    assert len(result["subtasks"]) >= 2
    assert result["needs_split"] == True
```

**Step 2: 运行测试确认失败**

Run: `cd todo-mcp && uv run pytest tests/test_agent.py::test_estimate_task_tool tests/test_agent.py::test_split_task_tool -v`
Expected: FAIL

**Step 3: 添加新工具到 tools.py**

```python
# 在 todo-mcp/src/todo_mcp/agent/tools.py 末尾添加

from todo_mcp.utils.estimator import TaskEstimator

# ... 现有代码 ...


@tool
def estimate_task(content: str, priority: Optional[str] = None) -> dict:
    """预估任务完成时间。

    Args:
        content: 任务内容
        priority: 优先级 (high/medium/low)

    Returns:
        预估结果，包含 estimated_minutes, should_split, reason
    """
    config = _get_config()
    estimator = TaskEstimator(
        threshold_minutes=config.task_split_threshold_minutes,
        target_minutes=config.task_split_target_minutes
    )
    return estimator.estimate(content, priority)


@tool
def split_task(
    content: str,
    priority: Optional[str] = None,
    target_minutes: int = 60
) -> dict:
    """拆分任务为子任务。

    Args:
        content: 任务内容
        priority: 优先级 (high/medium/low)
        target_minutes: 每个子任务的目标时长（分钟）

    Returns:
        拆分结果，包含 subtasks 列表和 total_minutes
    """
    config = _get_config()
    estimator = TaskEstimator(
        threshold_minutes=config.task_split_threshold_minutes,
        target_minutes=config.task_split_target_minutes
    )
    return estimator.split(content, priority, target_minutes)


@tool
def add_task_with_split(
    content: str,
    time_expr: str,
    priority: Optional[str] = None,
    confirm_split: bool = True
) -> str:
    """添加任务，自动检测是否需要拆分。

    如果预估时间超过阈值，会返回拆分建议供用户确认。

    Args:
        content: 任务内容
        time_expr: 时间表达式，如"今天"、"明天"
        priority: 优先级 (high/medium/low)
        confirm_split: 是否需要用户确认拆分

    Returns:
        操作结果或拆分建议
    """
    config = _get_config()
    estimator = TaskEstimator(
        threshold_minutes=config.task_split_threshold_minutes,
        target_minutes=config.task_split_target_minutes
    )

    # 预估时间
    estimate = estimator.estimate(content, priority)

    if estimate["should_split"] and confirm_split:
        # 返回拆分建议
        split_result = estimator.split(content, priority)
        subtask_list = "\n".join([
            f"  - {s['content']} (预估: {s['estimated_minutes']}m)"
            for s in split_result["subtasks"]
        ])
        return (
            f"⏱️ 预估此任务需要 {estimate['estimated_minutes']} 分钟，建议拆分：\n"
            f"{subtask_list}\n\n"
            f"请确认：\n"
            f"[1] 按建议拆分\n"
            f"[2] 直接添加（不拆分）"
        )

    # 直接添加任务
    return add_task.invoke({
        "content": content,
        "time_expr": time_expr,
        "priority": priority
    })


def get_all_tools():
    """获取所有工具列表。"""
    return [
        add_task,
        get_today,
        list_plans,
        update_task,
        get_progress,
        analyze_status,
        suggest_schedule,
        # 新增工具
        estimate_task,
        split_task,
        add_task_with_split,
    ]
```

**Step 4: 运行测试确认通过**

Run: `cd todo-mcp && uv run pytest tests/test_agent.py -v`
Expected: PASS

**Step 5: 提交**

```bash
git add todo-mcp/src/todo_mcp/agent/tools.py todo-mcp/tests/test_agent.py
git commit -m "feat(agent): add estimate_task, split_task, add_task_with_split tools"
```

---

## Task 7: 更新 Agent 提示词

**Files:**
- Modify: `todo-mcp/src/todo_mcp/agent/prompts.py`

**Step 1: 更新系统提示词**

```python
# 修改 todo-mcp/src/todo_mcp/agent/prompts.py

SYSTEM_PROMPT = """你是一个个人计划管理助手，帮助用户管理日常任务和计划。

你可以帮助用户：
- 添加、查看、更新任务
- 分析任务完成进度
- 提供智能安排建议
- 拆分复杂任务并预估完成时间

## 任务拆分规则

当用户添加任务时：
1. 先预估任务完成时间（使用 estimate_task 工具）
2. 如果预估超过 2 小时，询问用户是否需要拆分
3. 拆分时，每个子任务控制在 30-60 分钟

## 时间预估规则

- high 优先级：需要更仔细，预估时间 ×1.2
- low 优先级：可以快速完成，预估时间 ×0.8
- 复杂任务（涉及多个步骤）：按步骤分别估算后求和

## 拆分命令

用户可以说：
- "帮我把 [任务] 拆分一下"
- "拆分 [任务ID]"
- "这个任务太大了，拆小一点"

## 自动完成规则

当一个任务的所有子任务都完成时，自动将父任务标记为完成。

当前日期: {current_date}
"""


def get_system_prompt() -> str:
    """获取系统提示词。"""
    from datetime import date
    today = date.today()
    return SYSTEM_PROMPT.format(current_date=today.strftime("%Y年%m月%d日"))
```

**Step 2: 提交**

```bash
git add todo-mcp/src/todo_mcp/agent/prompts.py
git commit -m "feat(prompts): update system prompt with task splitting rules"
```

---

## Task 8: 更新 update_task 支持自动完成父任务

**Files:**
- Modify: `todo-mcp/src/todo_mcp/agent/tools.py`

**Step 1: 修改 update_task 函数**

在 `update_task` 函数中添加自动完成父任务的逻辑：

```python
# 修改 todo-mcp/src/todo_mcp/agent/tools.py 中的 update_task 函数

@tool
def update_task(task_id: str, status: Optional[str] = None) -> str:
    """更新任务状态。

    Args:
        task_id: 任务ID
        status: 新状态，可选值: completed, pending

    Returns:
        操作结果消息
    """
    config = _get_config()

    try:
        parts = task_id.split("-")
        if len(parts) >= 4:
            year = parts[0]
            quarter = parts[1].replace("Q", "") if "Q" in parts[1] else parts[1]
            month = parts[2] if "Q" in parts[1] else parts[1]

            month_names = {
                "01": "01-January", "02": "02-February", "03": "03-March",
                "04": "04-April", "05": "05-May", "06": "06-June",
                "07": "07-July", "08": "08-August", "09": "09-September",
                "10": "10-October", "11": "11-November", "12": "12-December"
            }
            month_file = month_names.get(month, f"{month}-Month")
            file_path = config.todo_root / year / f"Q{quarter}" / f"{month_file}.md"

            if not file_path.exists():
                return f"错误: 找不到任务文件"

            writer = MarkdownWriter(file_path)
            reader = MarkdownReader(file_path)

            if status:
                new_status = TaskStatus.COMPLETED if status.lower() in ["completed", "done", "完成"] else TaskStatus.PENDING
                success = writer.update_task_status(task_id, new_status)

                if success and new_status == TaskStatus.COMPLETED and config.auto_complete_parent:
                    # 检查是否需要自动完成父任务
                    tasks = reader.read_tasks()
                    task = next((t for t in tasks if t.id == task_id), None)

                    if task and task.parent_id:
                        parent = next((t for t in tasks if t.id == task.parent_id), None)
                        if parent:
                            # 检查所有子任务是否完成
                            all_subtasks = [t for t in tasks if t.parent_id == parent.id]
                            all_completed = all(t.status == TaskStatus.COMPLETED for t in all_subtasks)

                            if all_completed:
                                writer.update_task_status(parent.id, TaskStatus.COMPLETED)
                                return f"任务状态已更新为: {new_status.value}\n🎉 所有子任务已完成，父任务「{parent.content}」已自动标记为完成！"

                if success:
                    return f"任务状态已更新为: {new_status.value}"
                else:
                    return "更新任务状态失败"

            return "任务已更新"
        else:
            return f"错误: 无效的 task_id 格式: {task_id}"
    except Exception as e:
        return f"错误: {str(e)}"
```

**Step 2: 提交**

```bash
git add todo-mcp/src/todo_mcp/agent/tools.py
git commit -m "feat(update_task): auto-complete parent when all subtasks done"
```

---

## Task 9: 运行完整测试

**Step 1: 运行所有测试**

Run: `cd todo-mcp && uv run pytest -v`
Expected: All PASS

**Step 2: 修复任何失败的测试**

如有失败，逐个修复后重新运行。

---

## Task 10: 最终提交

**Step 1: 检查所有更改**

Run: `git status`

**Step 2: 确保所有文件已提交**

如有未提交的文件，添加并提交。

**Step 3: 创建总结**

Run: `git log --oneline -10`

---

## 完成检查清单

- [ ] Task 模型支持 parent_id, estimated_minutes, subtask_ids
- [ ] Config 模型支持任务拆分配置
- [ ] MarkdownReader 能解析层级任务和预估时间
- [ ] MarkdownWriter 能写入层级任务和预估时间
- [ ] TaskEstimator 提供时间预估和拆分功能
- [ ] Agent 工具：estimate_task, split_task, add_task_with_split
- [ ] 系统提示词包含任务拆分规则
- [ ] update_task 支持自动完成父任务
- [ ] 所有测试通过
