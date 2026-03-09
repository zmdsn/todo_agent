# src/todo_mcp/parser/reader.py
from pathlib import Path
import re
from typing import List
from todo_mcp.models import Task, TaskStatus


class MarkdownReader:
    TASK_PATTERN = re.compile(r"^(-|\*)\s+\[([ xX])\]\s+(.+)$", re.MULTILINE)
    DAY_PATTERN = re.compile(r"^#+\s+(\d{1,2})/(\d{1,2})", re.MULTILINE)

    def __init__(self, file_path: Path):
        self.file_path = file_path

    def read_tasks(self) -> List[Task]:
        if not self.file_path.exists():
            return []

        content = self.file_path.read_text(encoding='utf-8')
        tasks = []
        current_day = None
        task_counter = 0

        lines = content.split('\n')
        for line in lines:
            # 检查日期标题
            day_match = self.DAY_PATTERN.match(line.strip())
            if day_match:
                current_day = int(day_match.group(2))
                task_counter = 0
                continue

            # 检查任务
            task_match = self.TASK_PATTERN.match(line.strip())
            if task_match:
                task_counter += 1
                status = TaskStatus.COMPLETED if task_match.group(2).lower() == 'x' else TaskStatus.PENDING
                content_text = task_match.group(3).strip()

                task = Task(
                    id=self._generate_task_id(current_day, task_counter),
                    content=content_text,
                    status=status,
                    location=str(self.file_path)
                )
                tasks.append(task)

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
