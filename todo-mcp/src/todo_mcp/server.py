from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from typing import List, Optional
from pathlib import Path
from datetime import date
import json
import sys
import os

from todo_mcp.models import Task, TaskStatus, Config
from todo_mcp.utils.time import TimeParser
from todo_mcp.parser.writer import MarkdownWriter
from todo_mcp.parser.reader import MarkdownReader


class TodoMCPServer:
    """Todo MCP Server implementation."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self._task_counter = 0

    def _generate_task_id(self, year: int, quarter: int, month: int, day: Optional[int] = None) -> str:
        """Generate a unique task ID."""
        self._task_counter += 1
        day_part = f"-{day}" if day else ""
        return f"{year}-{quarter}-{month}{day_part}-{self._task_counter}"

    async def _handle_add_task(self, arguments: dict) -> List[TextContent]:
        """Handle add_task tool call."""
        content = arguments["content"]
        time_expr = arguments["time_expr"]
        priority = arguments.get("priority")
        due_date = arguments.get("due_date")

        # Parse time expression
        parser = TimeParser()
        parsed = parser.parse(time_expr)

        # Get file path (remove anchor if present)
        file_path_str = parsed.to_file_path()
        if "#" in file_path_str:
            file_path_str = file_path_str.split("#")[0]
        file_path = self.config.todo_root / file_path_str

        # Ensure file exists
        writer = MarkdownWriter(file_path)
        if not file_path.exists():
            writer.ensure_file_exists(parsed.year, parsed.quarter, parsed.month)

        # Create task
        task = Task(
            id=self._generate_task_id(
                parsed.year, parsed.quarter, parsed.month, parsed.day
            ),
            content=content,
            status=TaskStatus.PENDING,
            location=str(file_path),
            priority=priority,
            due_date=due_date
        )

        # Add task to file
        writer.add_task(task, day=parsed.day)

        return [TextContent(type="text", text=f"已添加任务: {content} 到 {time_expr}")]

    async def _handle_get_today(self, arguments: dict) -> List[TextContent]:
        """Handle get_today tool call - 获取今日任务概览."""
        today = date.today()
        parser = TimeParser()
        parsed = parser.parse("今天")

        # 构建今日文件路径
        file_path_str = parsed.to_file_path()
        if "#" in file_path_str:
            file_path_str = file_path_str.split("#")[0]
        file_path = self.config.todo_root / file_path_str

        # 读取任务
        reader = MarkdownReader(file_path)

        # 筛选今日任务 (通过日期标题匹配)
        today_tasks = []
        content = file_path.read_text(encoding='utf-8') if file_path.exists() else ""
        lines = content.split('\n')
        current_day = None
        task_counter = 0

        for line in lines:
            # 检查日期标题 (支持多种格式: #### 3/9 或 #### 9日)
            day = reader._parse_day_header(line.strip())
            if day is not None:
                current_day = day
                task_counter = 0
                continue

            # 检查任务
            task_match = MarkdownReader.TASK_PATTERN.match(line)
            if task_match and current_day == today.day:
                task_counter += 1
                status = TaskStatus.COMPLETED if task_match.group(3).lower() == 'x' else TaskStatus.PENDING
                task = Task(
                    id=f"{today.year}-{parsed.quarter}-{today.month:02d}-{today.day:02d}-{task_counter}",
                    content=task_match.group(4).strip(),
                    status=status,
                    location=str(file_path)
                )
                today_tasks.append(task)

        # 统计
        total = len(today_tasks)
        completed = sum(1 for t in today_tasks if t.status == TaskStatus.COMPLETED)
        pending = total - completed

        # 格式化输出
        result = f"📅 今日概览 ({today.year}/{today.month}/{today.day})\n\n"
        result += f"📊 统计: 总计 {total} 项任务, 已完成 {completed} 项, 待办 {pending} 项\n\n"

        if today_tasks:
            result += "📋 任务列表:\n"
            for i, task in enumerate(today_tasks, 1):
                status_icon = "✅" if task.status == TaskStatus.COMPLETED else "⬜"
                result += f"  #{i} {status_icon} {task.content}\n"
            result += f"\n💡 提示: 使用编号操作任务，如「完成 #1」「删除 #2」"
        else:
            result += "今日暂无任务安排 🎉"

        return [TextContent(type="text", text=result)]

    async def _handle_update_task(self, arguments: dict) -> List[TextContent]:
        """Handle update_task tool call - 更新任务状态或内容."""
        task_id = arguments.get("task_id")
        new_status = arguments.get("status")
        new_content = arguments.get("content")

        if not task_id:
            return [TextContent(type="text", text="错误: 缺少 task_id 参数")]

        # 解析 task_id 获取文件路径
        # 格式: {年}-{季}-{月}-{日}-{序号} 或 {年}-Q{季}-{月}-{日}-{序号}
        try:
            parts = task_id.split("-")
            if len(parts) >= 4:
                year = parts[0]
                quarter = parts[1].replace("Q", "") if "Q" in parts[1] else parts[1]
                month = parts[2] if "Q" in parts[1] else parts[1]
                # 找到月份文件
                month_names = {
                    "01": "01-January", "02": "02-February", "03": "03-March",
                    "04": "04-April", "05": "05-May", "06": "06-June",
                    "07": "07-July", "08": "08-August", "09": "09-September",
                    "10": "10-October", "11": "11-November", "12": "12-December"
                }
                month_file = month_names.get(month, f"{month}-Month")
                file_path = self.config.todo_root / year / f"Q{quarter}" / f"{month_file}.md"

                if not file_path.exists():
                    return [TextContent(type="text", text=f"错误: 找不到任务文件 {file_path}")]

                writer = MarkdownWriter(file_path)

                if new_status:
                    # 更新状态
                    status = TaskStatus.COMPLETED if new_status.lower() in ["completed", "done", "完成"] else TaskStatus.PENDING
                    success = writer.update_task_status(task_id, status)
                    if success:
                        return [TextContent(type="text", text=f"任务状态已更新为: {status.value}")]
                    else:
                        return [TextContent(type="text", text="更新任务状态失败")]

                return [TextContent(type="text", text="任务已更新")]
            else:
                return [TextContent(type="text", text=f"错误: 无效的 task_id 格式: {task_id}")]
        except Exception as e:
            return [TextContent(type="text", text=f"错误: {str(e)}")]

    async def _handle_get_progress(self, arguments: dict) -> List[TextContent]:
        """Handle get_progress tool call - 获取完成进度."""
        time_expr = arguments.get("time_expr", "本月")
        parser = TimeParser()
        parsed = parser.parse(time_expr)

        # 获取文件路径
        file_path_str = parsed.to_file_path()
        if "#" in file_path_str:
            file_path_str = file_path_str.split("#")[0]
        file_path = self.config.todo_root / file_path_str

        # 读取任务
        reader = MarkdownReader(file_path)
        tasks = reader.read_tasks()

        # 统计
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        pending = total - completed
        progress = (completed / total * 100) if total > 0 else 0

        result = f"📈 进度报告 ({time_expr})\n\n"
        result += f"📊 统计:\n"
        result += f"  - 总任务: {total} 项\n"
        result += f"  - 已完成: {completed} 项\n"
        result += f"  - 待办: {pending} 项\n"
        result += f"  - 完成率: {progress:.1f}%\n"

        # 进度条
        bar_length = 20
        filled = int(bar_length * progress / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        result += f"\n进度: [{bar}] {progress:.1f}%\n"

        return [TextContent(type="text", text=result)]

    async def _handle_list_plans(self, arguments: dict) -> List[TextContent]:
        """Handle list_plans tool call - 列出指定时间范围的计划."""
        time_expr = arguments.get("time_expr", "本月")
        include_completed = arguments.get("include_completed", True)

        parser = TimeParser()
        parsed = parser.parse(time_expr)

        # 获取文件路径
        file_path_str = parsed.to_file_path()
        if "#" in file_path_str:
            file_path_str = file_path_str.split("#")[0]
        file_path = self.config.todo_root / file_path_str

        # 读取任务
        reader = MarkdownReader(file_path)
        tasks = reader.read_tasks()

        # 过滤
        if not include_completed:
            tasks = [t for t in tasks if t.status != TaskStatus.COMPLETED]

        result = f"📋 计划列表 ({time_expr})\n\n"

        if not tasks:
            result += "暂无计划项"
        else:
            for i, task in enumerate(tasks, 1):
                status_icon = "✅" if task.status == TaskStatus.COMPLETED else "⬜"
                result += f"{i}. {status_icon} {task.content}\n"
                result += f"   ID: {task.id}\n"

        return [TextContent(type="text", text=result)]

    async def _handle_create_plan(self, arguments: dict) -> List[TextContent]:
        """Handle create_plan tool call - 创建计划文件."""
        time_expr = arguments.get("time_expr")
        template = arguments.get("template", "default")

        if not time_expr:
            return [TextContent(type="text", text="错误: 缺少 time_expr 参数")]

        parser = TimeParser()
        parsed = parser.parse(time_expr)

        # 获取文件路径
        file_path_str = parsed.to_file_path()
        if "#" in file_path_str:
            file_path_str = file_path_str.split("#")[0]
        file_path = self.config.todo_root / file_path_str

        if file_path.exists():
            return [TextContent(type="text", text=f"计划文件已存在: {file_path}")]

        # 创建文件
        writer = MarkdownWriter(file_path)
        if parsed.resolution.value in ["month", "day", "week"]:
            writer.ensure_file_exists(parsed.year, parsed.quarter, parsed.month)
            return [TextContent(type="text", text=f"已创建计划文件: {file_path}")]
        elif parsed.resolution.value == "quarter":
            file_path.parent.mkdir(parents=True, exist_ok=True)
            content = f"# Q{parsed.quarter} 季度计划\n\n"
            content += f"> {parsed.year}年 第{parsed.quarter}季度\n\n"
            content += "## 季度目标\n\n1. [目标1]\n\n"
            content += "## 重点事项\n\n"
            file_path.write_text(content, encoding='utf-8')
            return [TextContent(type="text", text=f"已创建季度计划文件: {file_path}")]
        elif parsed.resolution.value == "year":
            file_path.parent.mkdir(parents=True, exist_ok=True)
            content = f"# {parsed.year} 年度计划\n\n"
            content += f"> {parsed.year}年\n\n"
            content += "## 年度目标\n\n1. [目标1]\n\n"
            content += "## 关键结果\n\n"
            file_path.write_text(content, encoding='utf-8')
            return [TextContent(type="text", text=f"已创建年度计划文件: {file_path}")]

        return [TextContent(type="text", text=f"已创建计划文件: {file_path}")]

    async def _handle_delete_task(self, arguments: dict) -> List[TextContent]:
        """Handle delete_task tool call - 删除任务."""
        task_id = arguments.get("task_id")

        if not task_id:
            return [TextContent(type="text", text="错误: 缺少 task_id 参数")]

        # 解析 task_id 获取文件路径
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
                file_path = self.config.todo_root / year / f"Q{quarter}" / f"{month_file}.md"

                if not file_path.exists():
                    return [TextContent(type="text", text=f"错误: 找不到任务文件")]

                writer = MarkdownWriter(file_path)
                success = writer.delete_task(task_id)

                if success:
                    return [TextContent(type="text", text=f"任务已删除: {task_id}")]
                else:
                    return [TextContent(type="text", text="删除任务失败")]
            else:
                return [TextContent(type="text", text=f"错误: 无效的 task_id 格式")]
        except Exception as e:
            return [TextContent(type="text", text=f"错误: {str(e)}")]

    async def _handle_move_task(self, arguments: dict) -> List[TextContent]:
        """Handle move_task tool call - 移动任务到其他时间."""
        task_id = arguments.get("task_id")
        target_time = arguments.get("target_time")

        if not task_id or not target_time:
            return [TextContent(type="text", text="错误: 缺少必要参数")]

        # 解析源任务
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
                source_path = self.config.todo_root / year / f"Q{quarter}" / f"{month_file}.md"

                if not source_path.exists():
                    return [TextContent(type="text", text=f"错误: 找不到源任务文件")]

                # 读取源任务
                reader = MarkdownReader(source_path)
                tasks = reader.read_tasks()
                task_to_move = None
                for task in tasks:
                    if task.id == task_id:
                        task_to_move = task
                        break

                if not task_to_move:
                    return [TextContent(type="text", text=f"错误: 找不到任务 {task_id}")]

                # 解析目标时间
                parser = TimeParser()
                target_parsed = parser.parse(target_time)
                target_path_str = target_parsed.to_file_path()
                if "#" in target_path_str:
                    target_path_str = target_path_str.split("#")[0]
                target_path = self.config.todo_root / target_path_str

                # 确保目标文件存在
                writer = MarkdownWriter(target_path)
                if not target_path.exists():
                    writer.ensure_file_exists(target_parsed.year, target_parsed.quarter, target_parsed.month)

                # 添加到目标位置
                writer.add_task(task_to_move, day=target_parsed.day)

                # 从源位置删除 (简化处理)
                source_writer = MarkdownWriter(source_path)
                source_writer.delete_task(task_id)

                return [TextContent(type="text", text=f"任务已移动到: {target_time}")]
            else:
                return [TextContent(type="text", text=f"错误: 无效的 task_id 格式")]
        except Exception as e:
            return [TextContent(type="text", text=f"错误: {str(e)}")]

    async def _handle_get_reminders(self, arguments: dict) -> List[TextContent]:
        """Handle get_reminders tool call - 获取提醒."""
        days = arguments.get("days", self.config.default_reminder_days)

        today = date.today()
        parser = TimeParser()

        # 获取本月文件
        parsed = parser.parse("本月")
        file_path_str = parsed.to_file_path()
        if "#" in file_path_str:
            file_path_str = file_path_str.split("#")[0]
        file_path = self.config.todo_root / file_path_str

        if not file_path.exists():
            return [TextContent(type="text", text="暂无提醒事项")]

        reader = MarkdownReader(file_path)
        tasks = reader.read_tasks()

        # 筛选待办任务
        pending_tasks = [t for t in tasks if t.status == TaskStatus.PENDING]

        result = f"🔔 提醒事项 (未来 {days} 天)\n\n"

        if not pending_tasks:
            result += "暂无待办事项 🎉"
        else:
            for task in pending_tasks:
                result += f"⬜ {task.content}\n"
                if task.due_date:
                    result += f"   截止: {task.due_date}\n"

        return [TextContent(type="text", text=result)]

    async def _handle_analyze_status(self, arguments: dict) -> List[TextContent]:
        """Handle analyze_status tool call - 分析计划健康状态."""
        time_expr = arguments.get("time_expr", "本月")
        parser = TimeParser()
        parsed = parser.parse(time_expr)

        file_path_str = parsed.to_file_path()
        if "#" in file_path_str:
            file_path_str = file_path_str.split("#")[0]
        file_path = self.config.todo_root / file_path_str

        if not file_path.exists():
            return [TextContent(type="text", text=f"计划文件不存在: {time_expr}")]

        reader = MarkdownReader(file_path)
        tasks = reader.read_tasks()

        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        pending = total - completed
        progress = (completed / total * 100) if total > 0 else 0

        # 健康度评估
        if progress >= 80:
            health = "优秀"
            emoji = "🌟"
        elif progress >= 60:
            health = "良好"
            emoji = "👍"
        elif progress >= 40:
            health = "一般"
            emoji = "⚠️"
        else:
            health = "需要关注"
            emoji = "🔴"

        result = f"📊 计划健康状态分析 ({time_expr})\n\n"
        result += f"{emoji} 健康度: {health}\n\n"
        result += f"📈 统计数据:\n"
        result += f"  - 总任务: {total} 项\n"
        result += f"  - 已完成: {completed} 项\n"
        result += f"  - 待办: {pending} 项\n"
        result += f"  - 完成率: {progress:.1f}%\n\n"

        # 建议
        result += "💡 建议:\n"
        if progress < 50:
            result += "  - 建议重新评估任务优先级\n"
            result += "  - 考虑拆分大任务为小任务\n"
        elif progress < 80:
            result += "  - 继续保持当前节奏\n"
            result += "  - 关注即将到期的任务\n"
        else:
            result += "  - 表现优秀，继续保持!\n"
            result += "  - 可以考虑增加更多挑战性任务\n"

        return [TextContent(type="text", text=result)]

    async def _handle_generate_report(self, arguments: dict) -> List[TextContent]:
        """Handle generate_report tool call - 生成进度报告."""
        time_expr = arguments.get("time_expr", "本周")
        format_type = arguments.get("format", "text")
        parser = TimeParser()
        parsed = parser.parse(time_expr)

        file_path_str = parsed.to_file_path()
        if "#" in file_path_str:
            file_path_str = file_path_str.split("#")[0]
        file_path = self.config.todo_root / file_path_str

        if not file_path.exists():
            return [TextContent(type="text", text=f"计划文件不存在: {time_expr}")]

        reader = MarkdownReader(file_path)
        tasks = reader.read_tasks()

        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        pending = total - completed
        progress = (completed / total * 100) if total > 0 else 0

        if format_type == "markdown":
            result = f"# 进度报告: {time_expr}\n\n"
            result += f"## 概览\n\n"
            result += f"- 总任务: {total}\n"
            result += f"- 已完成: {completed}\n"
            result += f"- 待办: {pending}\n"
            result += f"- 完成率: {progress:.1f}%\n\n"
            result += f"## 已完成任务\n\n"
            for task in tasks:
                if task.status == TaskStatus.COMPLETED:
                    result += f"- [x] {task.content}\n"
            result += f"\n## 待办任务\n\n"
            for task in tasks:
                if task.status == TaskStatus.PENDING:
                    result += f"- [ ] {task.content}\n"
        else:
            result = f"📄 进度报告 ({time_expr})\n\n"
            result += f"{'='*40}\n"
            result += f"📊 统计概览\n"
            result += f"{'='*40}\n"
            result += f"总任务: {total} 项\n"
            result += f"已完成: {completed} 项\n"
            result += f"待办: {pending} 项\n"
            result += f"完成率: {progress:.1f}%\n\n"

            result += f"{'='*40}\n"
            result += f"✅ 已完成任务\n"
            result += f"{'='*40}\n"
            for task in tasks:
                if task.status == TaskStatus.COMPLETED:
                    result += f"  • {task.content}\n"

            result += f"\n{'='*40}\n"
            result += f"⬜ 待办任务\n"
            result += f"{'='*40}\n"
            for task in tasks:
                if task.status == TaskStatus.PENDING:
                    result += f"  • {task.content}\n"

        return [TextContent(type="text", text=result)]


def create_server(config: Optional[Config] = None) -> Server:
    """Create the MCP server instance."""
    server = Server("todo-mcp")
    todo_server = TodoMCPServer(config)

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name="add_task",
                description="添加任务到指定时间",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "任务内容"},
                        "time_expr": {"type": "string", "description": "时间表达，如'今天'、'本周'"},
                        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                        "due_date": {"type": "string", "description": "截止日期"}
                    },
                    "required": ["content", "time_expr"]
                }
            ),
            Tool(
                name="get_today",
                description="获取今日任务概览",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="update_task",
                description="更新任务状态或内容",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                        "status": {"type": "string", "enum": ["pending", "completed"], "description": "新状态"},
                        "content": {"type": "string", "description": "新内容"}
                    },
                    "required": ["task_id"]
                }
            ),
            Tool(
                name="get_progress",
                description="获取完成进度",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "time_expr": {"type": "string", "description": "时间范围，如'今天'、'本周'、'本月'"}
                    }
                }
            ),
            Tool(
                name="list_plans",
                description="列出指定时间范围的计划",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "time_expr": {"type": "string", "description": "时间范围，如'今天'、'本周'、'本月'"},
                        "include_completed": {"type": "boolean", "description": "是否包含已完成任务", "default": True}
                    }
                }
            ),
            Tool(
                name="create_plan",
                description="创建计划文件",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "time_expr": {"type": "string", "description": "时间范围，如'本月'、'Q1'、'2026'"},
                        "template": {"type": "string", "description": "模板类型", "default": "default"}
                    },
                    "required": ["time_expr"]
                }
            ),
            Tool(
                name="delete_task",
                description="删除任务",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"}
                    },
                    "required": ["task_id"]
                }
            ),
            Tool(
                name="move_task",
                description="移动任务到其他时间",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                        "target_time": {"type": "string", "description": "目标时间，如'明天'、'下周'"}
                    },
                    "required": ["task_id", "target_time"]
                }
            ),
            Tool(
                name="get_reminders",
                description="获取提醒",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer", "description": "提前提醒天数", "default": 3}
                    }
                }
            ),
            Tool(
                name="analyze_status",
                description="分析计划健康状态",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "time_expr": {"type": "string", "description": "时间范围，默认为'本月'"}
                    }
                }
            ),
            Tool(
                name="generate_report",
                description="生成进度报告",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "time_expr": {"type": "string", "description": "时间范围，如'本周'、'本月'"},
                        "format": {"type": "string", "enum": ["text", "markdown"], "description": "报告格式"}
                    }
                }
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "add_task":
            return await todo_server._handle_add_task(arguments)
        elif name == "get_today":
            return await todo_server._handle_get_today(arguments)
        elif name == "update_task":
            return await todo_server._handle_update_task(arguments)
        elif name == "get_progress":
            return await todo_server._handle_get_progress(arguments)
        elif name == "list_plans":
            return await todo_server._handle_list_plans(arguments)
        elif name == "create_plan":
            return await todo_server._handle_create_plan(arguments)
        elif name == "delete_task":
            return await todo_server._handle_delete_task(arguments)
        elif name == "move_task":
            return await todo_server._handle_move_task(arguments)
        elif name == "get_reminders":
            return await todo_server._handle_get_reminders(arguments)
        elif name == "analyze_status":
            return await todo_server._handle_analyze_status(arguments)
        elif name == "generate_report":
            return await todo_server._handle_generate_report(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


async def async_main(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000):
    """Run the MCP server with specified transport."""
    server = create_server()

    if transport == "stdio":
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    elif transport == "streamable-http":
        from starlette.applications import Starlette
        from starlette.routing import Mount
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        import contextlib

        session_manager = StreamableHTTPSessionManager(server)

        @contextlib.asynccontextmanager
        async def lifespan(app: Starlette):
            async with session_manager.run():
                yield

        # Use session_manager as ASGI app directly via Mount
        app = Starlette(
            debug=True,
            routes=[Mount("/mcp", app=session_manager.handle_request)],
            lifespan=lifespan
        )

        import uvicorn
        config = uvicorn.Config(app, host=host, port=port)
        http_server = uvicorn.Server(config)
        await http_server.serve()
    else:
        raise ValueError(f"Unknown transport: {transport}")


def main():
    import asyncio

    # Parse command line arguments
    transport = "stdio"
    host = "127.0.0.1"
    port = 8000

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--transport":
            transport = args[i + 1]
            i += 2
        elif args[i] == "--host":
            host = args[i + 1]
            i += 2
        elif args[i] == "--port":
            port = int(args[i + 1])
            i += 2
        elif args[i] == "--http":
            transport = "streamable-http"
            i += 1
        else:
            i += 1

    print(f"Starting todo-mcp server with transport={transport}", file=sys.stderr)
    if transport == "streamable-http":
        print(f"HTTP server listening on http://{host}:{port}/mcp", file=sys.stderr)

    asyncio.run(async_main(transport=transport, host=host, port=port))


if __name__ == "__main__":
    main()
