# src/todo_mcp/parser/writer.py
from pathlib import Path
import re
from typing import Optional
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

    def add_task(self, task: Task, day: Optional[int] = None):
        """添加任务到文件"""
        content = self.file_path.read_text(encoding='utf-8') if self.file_path.exists() else ""

        if day:
            day_section = f"#### {day}日"
            task_line = f"- [ ] {task.content}\n"

            if day_section in content:
                content = content.replace(day_section, f"{day_section}\n{task_line}")
            else:
                content += f"\n{day_section}\n{task_line}"
        else:
            content += f"- [ ] {task.content}\n"

        self.file_path.write_text(content, encoding='utf-8')

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """更新任务状态"""
        if not self.file_path.exists():
            return False

        content = self.file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        for i, line in enumerate(lines):
            if re.match(r'^(-|\*)\s+\[[ xX]\]', line):
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
            if re.match(r'^(-|\*)\s+\[[ xX]\]', line):
                task_counter += 1
                if task_counter == 1:  # 简化：删除第一个任务
                    continue
            new_lines.append(line)

        self.file_path.write_text('\n'.join(new_lines), encoding='utf-8')
        return True
