# src/todo_mcp/parser/writer.py
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

    def _parse_task_id(self, task_id: str) -> Optional[dict]:
        """解析 task_id 获取日期和序号信息"""
        # 格式: {年}-Q{季}-{月}-{日}-{序号} 或 {年}-{季}-{月}-{日}-{序号}
        match = re.match(r'^(\d+)-Q?(\d+)-(\d+)-(\d+)-(\d+)$', task_id)
        if match:
            return {
                'year': int(match.group(1)),
                'quarter': int(match.group(2)),
                'month': int(match.group(3)),
                'day': int(match.group(4)),
                'index': int(match.group(5))
            }
        return None

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """更新任务状态"""
        if not self.file_path.exists():
            return False

        # 解析 task_id
        parsed = self._parse_task_id(task_id)
        if not parsed:
            return False

        target_day = parsed['day']
        target_index = parsed['index']

        content = self.file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        current_day = None
        task_counter = 0
        # 支持 "## 12日" 和 "#### 3/9" 两种格式
        day_cn_pattern = re.compile(r'^#+\s+(\d{1,2})[日号]')
        day_slash_pattern = re.compile(r'^#+\s+\d{1,2}/(\d{1,2})')
        task_pattern = re.compile(r'^(\s*)(-|\*)\s+\[[ xX]\]')

        for i, line in enumerate(lines):
            # 检查日期标题
            stripped = line.strip()
            cn_match = day_cn_pattern.match(stripped)
            slash_match = day_slash_pattern.match(stripped)
            if cn_match:
                current_day = int(cn_match.group(1))
                continue
            elif slash_match:
                current_day = int(slash_match.group(1))
                continue

            # 检查任务
            if task_pattern.match(line):
                if current_day == target_day:
                    task_counter += 1
                    if task_counter == target_index:
                        # 找到目标任务，更新状态
                        if status == TaskStatus.COMPLETED:
                            lines[i] = re.sub(r'\[ \]', '[x]', line)
                        else:
                            lines[i] = re.sub(r'\[x\]', '[ ]', line, flags=re.IGNORECASE)
                        self.file_path.write_text('\n'.join(lines), encoding='utf-8')
                        return True

        return False

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if not self.file_path.exists():
            return False

        # 解析 task_id
        parsed = self._parse_task_id(task_id)
        if not parsed:
            return False

        target_day = parsed['day']
        target_index = parsed['index']

        content = self.file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        new_lines = []

        current_day = None
        task_counter = 0
        # 支持 "## 12日" 和 "#### 3/9" 两种格式
        day_cn_pattern = re.compile(r'^#+\s+(\d{1,2})[日号]')
        day_slash_pattern = re.compile(r'^#+\s+\d{1,2}/(\d{1,2})')
        task_pattern = re.compile(r'^(\s*)(-|\*)\s+\[[ xX]\]')

        for line in lines:
            # 检查日期标题
            stripped = line.strip()
            cn_match = day_cn_pattern.match(stripped)
            slash_match = day_slash_pattern.match(stripped)
            if cn_match:
                current_day = int(cn_match.group(1))
                new_lines.append(line)
                continue
            elif slash_match:
                current_day = int(slash_match.group(1))
                new_lines.append(line)
                continue

            # 检查任务
            if task_pattern.match(line):
                if current_day == target_day:
                    task_counter += 1
                    if task_counter == target_index:
                        # 跳过要删除的任务
                        continue

            new_lines.append(line)

        self.file_path.write_text('\n'.join(new_lines), encoding='utf-8')
        return True

    def update_task_estimate(self, task_id: str, estimated_minutes: Optional[int]) -> bool:
        """更新任务预估时间。

        Args:
            task_id: 任务ID
            estimated_minutes: 预估分钟数，None 表示移除预估时间

        Returns:
            是否更新成功
        """
        if not self.file_path.exists():
            return False

        # 解析 task_id
        parsed = self._parse_task_id(task_id)
        if not parsed:
            return False

        target_day = parsed['day']
        target_index = parsed['index']

        content = self.file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        current_day = None
        task_counter = 0
        day_cn_pattern = re.compile(r'^#+\s+(\d{1,2})[日号]')
        day_slash_pattern = re.compile(r'^#+\s+\d{1,2}/(\d{1,2})')
        task_pattern = re.compile(r'^(\s*)(-|\*)\s+\[[ xX]\]\s+(.+)$')

        for i, line in enumerate(lines):
            # 检查日期标题
            stripped = line.strip()
            cn_match = day_cn_pattern.match(stripped)
            slash_match = day_slash_pattern.match(stripped)
            if cn_match:
                current_day = int(cn_match.group(1))
                continue
            elif slash_match:
                current_day = int(slash_match.group(1))
                continue

            # 检查任务
            task_match = task_pattern.match(line)
            if task_match:
                if current_day == target_day:
                    task_counter += 1
                    if task_counter == target_index:
                        # 找到目标任务，更新预估时间
                        indent = task_match.group(1)
                        bullet = task_match.group(2)
                        status_match = re.search(r'\[([ xX])\]', line)
                        status_str = status_match.group(0) if status_match else '[ ]'

                        # 提取原始内容，移除已有的预估时间
                        original_content = task_match.group(3)
                        # 移除已有的预估时间标记
                        original_content = re.sub(r'\s*\(预估:\s*[\d.]+[hm]\)\s*$', '', original_content).strip()

                        # 构建新的预估时间标记
                        estimate_str = ""
                        if estimated_minutes is not None:
                            hours = estimated_minutes / 60
                            if hours >= 1:
                                estimate_str = f" (预估: {hours:.0f}h)" if hours == int(hours) else f" (预估: {hours:.1f}h)"
                            else:
                                estimate_str = f" (预估: {estimated_minutes}m)"

                        lines[i] = f"{indent}{bullet} {status_str} {original_content}{estimate_str}"
                        self.file_path.write_text('\n'.join(lines), encoding='utf-8')
                        return True

        return False
