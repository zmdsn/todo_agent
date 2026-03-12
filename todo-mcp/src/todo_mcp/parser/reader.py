# src/todo_mcp/parser/reader.py
from pathlib import Path
import re
from typing import List, Optional
from todo_mcp.models import Task, TaskStatus


class MarkdownReader:
    TASK_PATTERN = re.compile(r"^(\s*)(-|\*)\s+\[([ xX])\]\s+(.+)$", re.MULTILINE)
    # 支持 "3/9" 格式和 "9日" 格式
    DAY_PATTERN = re.compile(r"^#+\s+(\d{1,2})/(\d{1,2})", re.MULTILINE)
    DAY_CN_PATTERN = re.compile(r"^#+\s+(\d{1,2})[日号]", re.MULTILINE)
    ESTIMATE_PATTERN = re.compile(r"\(预估:\s*([\d.]+)\s*([hm])\)")

    def __init__(self, file_path: Path):
        self.file_path = file_path

    def _parse_day_header(self, line: str) -> Optional[int]:
        """Parse day from header line, supporting multiple formats."""
        # 格式1: #### 3/9
        day_match = self.DAY_PATTERN.match(line.strip())
        if day_match:
            return int(day_match.group(2))

        # 格式2: #### 9日
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
        # 从文件路径解析年/季/月
        parts = self.file_path.parts
        year = parts[-3] if len(parts) >= 3 else "2026"
        quarter = parts[-2].replace("Q", "") if len(parts) >= 2 else "1"
        month_file = parts[-1].replace(".md", "")
        month = month_file.split("-")[0]

        day_str = f"{day:02d}" if day else "00"
        return f"{year}-Q{quarter}-{month}-{day_str}-{counter}"
