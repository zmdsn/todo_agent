# src/todo_mcp/parser/reader.py
from pathlib import Path
import re
from typing import List, Optional
from todo_mcp.models import Task, TaskStatus


class MarkdownReader:
    TASK_PATTERN = re.compile(r"^(-|\*)\s+\[([ xX])\]\s+(.+)$", re.MULTILINE)
    # 支持 "3/9" 格式和 "9日" 格式
    DAY_PATTERN = re.compile(r"^#+\s+(\d{1,2})/(\d{1,2})", re.MULTILINE)
    DAY_CN_PATTERN = re.compile(r"^#+\s+(\d{1,2})[日号]", re.MULTILINE)

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
            day = self._parse_day_header(line.strip())
            if day is not None:
                current_day = day
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
