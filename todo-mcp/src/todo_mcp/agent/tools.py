# todo-mcp/src/todo_mcp/agent/tools.py
"""LangChain tools for todo agent."""
from langchain_core.tools import tool
from typing import Optional, List
from pathlib import Path

from todo_mcp.models import Task, TaskStatus, Config
from todo_mcp.utils.time import TimeParser
from todo_mcp.utils.estimator import TaskEstimator
from todo_mcp.parser.writer import MarkdownWriter
from todo_mcp.parser.reader import MarkdownReader
from datetime import date


def _get_config() -> Config:
    """Get config instance."""
    return Config()


@tool
def add_task(content: str, time_expr: str, priority: Optional[str] = None) -> str:
    """添加任务到指定时间。

    Args:
        content: 任务内容
        time_expr: 时间表达式，如"今天"、"明天"、"本周"、"3月15日"
        priority: 优先级，可选值: high, medium, low

    Returns:
        操作结果消息
    """
    config = _get_config()
    parser = TimeParser()
    parsed = parser.parse(time_expr)

    file_path_str = parsed.to_file_path()
    if "#" in file_path_str:
        file_path_str = file_path_str.split("#")[0]
    file_path = config.todo_root / file_path_str

    writer = MarkdownWriter(file_path)
    if not file_path.exists():
        writer.ensure_file_exists(parsed.year, parsed.quarter, parsed.month)

    # 简单生成 ID
    task_id = f"{parsed.year}-{parsed.quarter}-{parsed.month}"

    task = Task(
        id=task_id,
        content=content,
        status=TaskStatus.PENDING,
        location=str(file_path),
        priority=priority
    )

    writer.add_task(task, day=parsed.day)
    return f"已添加任务: {content} 到 {time_expr}"


@tool
def get_today() -> str:
    """获取今日任务概览。

    Returns:
        今日任务列表和统计信息
    """
    config = _get_config()
    today = date.today()
    parser = TimeParser()
    parsed = parser.parse("今天")

    file_path_str = parsed.to_file_path()
    if "#" in file_path_str:
        file_path_str = file_path_str.split("#")[0]
    file_path = config.todo_root / file_path_str

    if not file_path.exists():
        return f"📅 今日概览 ({today.year}/{today.month}/{today.day})\n\n今日暂无任务安排 🎉"

    reader = MarkdownReader(file_path)
    tasks = reader.read_tasks()

    # 筛选今日任务
    today_tasks = []
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    current_day = None
    task_counter = 0

    for line in lines:
        day = reader._parse_day_header(line.strip())
        if day is not None:
            current_day = day
            task_counter = 0
            continue

        task_match = MarkdownReader.TASK_PATTERN.match(line.strip())
        if task_match and current_day == today.day:
            task_counter += 1
            status = TaskStatus.COMPLETED if task_match.group(2).lower() == 'x' else TaskStatus.PENDING
            task = Task(
                id=f"{today.year}-{parsed.quarter}-{today.month:02d}-{today.day:02d}-{task_counter}",
                content=task_match.group(3).strip(),
                status=status,
                location=str(file_path)
            )
            today_tasks.append(task)

    total = len(today_tasks)
    completed = sum(1 for t in today_tasks if t.status == TaskStatus.COMPLETED)
    pending = total - completed

    result = f"📅 今日概览 ({today.year}/{today.month}/{today.day})\n\n"
    result += f"📊 统计: 总计 {total} 项任务, 已完成 {completed} 项, 待办 {pending} 项\n\n"

    if today_tasks:
        result += "📋 任务列表:\n"
        for task in today_tasks:
            status_icon = "✅" if task.status == TaskStatus.COMPLETED else "⬜"
            result += f"  {status_icon} {task.content}\n"
    else:
        result += "今日暂无任务安排 🎉"

    return result


@tool
def list_plans(time_expr: str = "本月", include_completed: bool = True) -> str:
    """列出指定时间范围的计划。

    Args:
        time_expr: 时间范围，如"今天"、"本周"、"本月"
        include_completed: 是否包含已完成任务

    Returns:
        计划列表
    """
    config = _get_config()
    parser = TimeParser()
    parsed = parser.parse(time_expr)

    file_path_str = parsed.to_file_path()
    if "#" in file_path_str:
        file_path_str = file_path_str.split("#")[0]
    file_path = config.todo_root / file_path_str

    if not file_path.exists():
        return f"📋 计划列表 ({time_expr})\n\n暂无计划项"

    reader = MarkdownReader(file_path)
    tasks = reader.read_tasks()

    if not include_completed:
        tasks = [t for t in tasks if t.status != TaskStatus.COMPLETED]

    result = f"📋 计划列表 ({time_expr})\n\n"

    if not tasks:
        result += "暂无计划项"
    else:
        for i, task in enumerate(tasks, 1):
            status_icon = "✅" if task.status == TaskStatus.COMPLETED else "⬜"
            result += f"{i}. {status_icon} {task.content}\n"

    return result


@tool
def update_task(
    task_id: str,
    status: Optional[str] = None,
    estimated_minutes: Optional[int] = None
) -> str:
    """更新任务状态或预估时间。

    Args:
        task_id: 任务ID或简短编号（如 #1, #2）
        status: 新状态，可选值: completed, pending
        estimated_minutes: 预估完成时间（分钟），设为 0 可移除预估时间

    Returns:
        操作结果消息
    """
    config = _get_config()
    parser = TimeParser()

    # 支持简短编号（#1, #2 或 1, 2）- 转换为完整 task_id
    original_task_ref = task_id
    if task_id.startswith("#") or task_id.isdigit():
        number = int(task_id.lstrip("#"))
        today = date.today()
        parsed = parser.parse("今天")

        file_path_str = parsed.to_file_path()
        if "#" in file_path_str:
            file_path_str = file_path_str.split("#")[0]
        file_path = config.todo_root / file_path_str

        if not file_path.exists():
            return f"错误: 找不到今日任务文件"

        reader = MarkdownReader(file_path)
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        current_day = None
        task_counter = 0
        target_task_id = None

        for line in lines:
            day = reader._parse_day_header(line.strip())
            if day is not None:
                current_day = day
                task_counter = 0
                continue

            task_match = MarkdownReader.TASK_PATTERN.match(line)
            if task_match and current_day == today.day:
                task_counter += 1
                if task_counter == number:
                    target_task_id = f"{today.year}-{parsed.quarter}-{today.month:02d}-{today.day:02d}-{task_counter}"
                    break

        if not target_task_id:
            return f"错误: 找不到今日第 {number} 项任务"

        task_id = target_task_id

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
            file_path = config.todo_root / year / f"Q{quarter}" / f"{month_file}.md"

            if not file_path.exists():
                return f"错误: 找不到任务文件"

            writer = MarkdownWriter(file_path)
            reader = MarkdownReader(file_path)
            results = []

            # 更新状态
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
                                results.append(f"🎉 所有子任务已完成，父任务「{parent.content}」已自动标记为完成")

                if success:
                    results.append(f"状态已更新为: {new_status.value}")
                else:
                    results.append("更新任务状态失败")

            # 更新预估时间
            if estimated_minutes is not None:
                # 0 表示移除预估时间
                estimate_value = None if estimated_minutes == 0 else estimated_minutes
                success = writer.update_task_estimate(task_id, estimate_value)
                if success:
                    if estimate_value is None:
                        results.append("已移除预估时间")
                    else:
                        hours = estimate_value / 60
                        if hours >= 1:
                            time_str = f"{hours:.0f}小时" if hours == int(hours) else f"{hours:.1f}小时"
                        else:
                            time_str = f"{estimate_value}分钟"
                        results.append(f"预估时间已更新为: {time_str}")
                else:
                    results.append("更新预估时间失败")

            if results:
                return f"任务 {original_task_ref} 更新结果:\n" + "\n".join(f"  - {r}" for r in results)
            return "任务已更新（无变更）"
        else:
            return f"错误: 无效的 task_id 格式: {task_id}"
    except Exception as e:
        return f"错误: {str(e)}"


@tool
def get_progress(time_expr: str = "本月") -> str:
    """获取完成进度。

    Args:
        time_expr: 时间范围，如"今天"、"本周"、"本月"

    Returns:
        进度统计信息
    """
    config = _get_config()
    parser = TimeParser()
    parsed = parser.parse(time_expr)

    file_path_str = parsed.to_file_path()
    if "#" in file_path_str:
        file_path_str = file_path_str.split("#")[0]
    file_path = config.todo_root / file_path_str

    if not file_path.exists():
        return f"📈 进度报告 ({time_expr})\n\n暂无数据"

    reader = MarkdownReader(file_path)
    tasks = reader.read_tasks()

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

    bar_length = 20
    filled = int(bar_length * progress / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    result += f"\n进度: [{bar}] {progress:.1f}%\n"

    return result


@tool
def analyze_status(time_expr: str = "本月") -> str:
    """分析计划健康状态。

    Args:
        time_expr: 时间范围，默认为"本月"

    Returns:
        健康状态分析和建议
    """
    config = _get_config()
    parser = TimeParser()
    parsed = parser.parse(time_expr)

    file_path_str = parsed.to_file_path()
    if "#" in file_path_str:
        file_path_str = file_path_str.split("#")[0]
    file_path = config.todo_root / file_path_str

    if not file_path.exists():
        return f"计划文件不存在: {time_expr}"

    reader = MarkdownReader(file_path)
    tasks = reader.read_tasks()

    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
    pending = total - completed
    progress = (completed / total * 100) if total > 0 else 0

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

    return result


@tool
def suggest_schedule() -> str:
    """智能安排建议，基于当前任务情况给出优化建议。

    Returns:
        智能安排建议
    """
    config = _get_config()
    today = date.today()
    parser = TimeParser()

    # 获取本月任务
    parsed = parser.parse("本月")
    file_path_str = parsed.to_file_path()
    if "#" in file_path_str:
        file_path_str = file_path_str.split("#")[0]
    file_path = config.todo_root / file_path_str

    if not file_path.exists():
        return "💡 暂无任务数据，请先添加任务"

    reader = MarkdownReader(file_path)
    tasks = reader.read_tasks()

    pending_tasks = [t for t in tasks if t.status == TaskStatus.PENDING]

    if not pending_tasks:
        return "🎉 所有任务已完成！本周可以安排一些新目标。"

    result = "💡 智能安排建议\n\n"

    # 按优先级分组
    high_priority = [t for t in pending_tasks if t.priority == "high"]
    medium_priority = [t for t in pending_tasks if t.priority == "medium"]
    low_priority = [t for t in pending_tasks if t.priority == "low" or t.priority is None]

    result += "📋 待办任务优先级分布:\n"
    result += f"  - 高优先级: {len(high_priority)} 项\n"
    result += f"  - 中优先级: {len(medium_priority)} 项\n"
    result += f"  - 低优先级: {len(low_priority)} 项\n\n"

    result += "📅 建议安排:\n"
    if high_priority:
        result += f"  1. 首先处理高优先级任务（{len(high_priority)}项）\n"
        for t in high_priority[:3]:
            result += f"     - {t.content}\n"
    if medium_priority:
        result += f"  2. 其次处理中优先级任务（{len(medium_priority)}项）\n"
    if low_priority:
        result += f"  3. 最后处理低优先级任务（{len(low_priority)}项）\n"

    result += f"\n⏰ 建议每天处理 2-3 个任务，预计 {len(pending_tasks) // 2 + 1} 天完成所有待办。"

    return result


def get_all_tools():
    """获取所有工具列表。"""
    return [
        add_task,
        get_today,
        list_plans,
        update_task,
        delete_task,
        get_progress,
        analyze_status,
        suggest_schedule,
        # 新增工具
        estimate_task,
        split_task,
        add_task_with_split,
    ]


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


@tool
def delete_task(task_ref: str) -> str:
    """删除指定任务。

    Args:
        task_ref: 任务引用，可以是:
            - 任务编号（如 #1, #2 或 1, 2）- 删除今日任务
            - 完整任务ID（如 2026-Q1-03-13-1）

    Returns:
        操作结果消息
    """
    config = _get_config()

    try:
        # 支持简短编号（#1, #2 或 1, 2）
        if task_ref.startswith("#") or task_ref.isdigit():
            # 获取今日任务
            number = int(task_ref.lstrip("#"))
            today = date.today()
            parser = TimeParser()
            parsed = parser.parse("今天")

            file_path_str = parsed.to_file_path()
            if "#" in file_path_str:
                file_path_str = file_path_str.split("#")[0]
            file_path = config.todo_root / file_path_str

            if not file_path.exists():
                return f"错误: 找不到今日任务文件"

            reader = MarkdownReader(file_path)
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            current_day = None
            task_counter = 0
            target_task_id = None

            for line in lines:
                day = reader._parse_day_header(line.strip())
                if day is not None:
                    current_day = day
                    task_counter = 0
                    continue

                task_match = MarkdownReader.TASK_PATTERN.match(line)
                if task_match and current_day == today.day:
                    task_counter += 1
                    if task_counter == number:
                        target_task_id = f"{today.year}-{parsed.quarter}-{today.month:02d}-{today.day:02d}-{task_counter}"
                        break

            if not target_task_id:
                return f"错误: 找不到今日第 {number} 项任务"

            task_id = target_task_id
            task_ref_display = f"#{number}"
        else:
            task_id = task_ref
            task_ref_display = task_ref

        # 解析 task_id 获取文件路径
        # task_id 格式: 2026-Q1-03-13-1 或 2026-1-03-13-1
        parts = task_id.split("-")
        if len(parts) >= 5:
            year = parts[0]
            # 支持 Q1 和 1 两种格式
            if "Q" in parts[1]:
                quarter = parts[1].replace("Q", "")
                month = parts[2]
            else:
                quarter = parts[1]
                month = parts[2]

            month_names = {
                "01": "01-January", "02": "02-February", "03": "03-March",
                "04": "04-April", "05": "05-May", "06": "06-June",
                "07": "07-July", "08": "08-August", "09": "09-September",
                "10": "10-October", "11": "11-November", "12": "12-December"
            }
            month_file = month_names.get(month, f"{month}-Month")
            file_path = config.todo_root / year / f"Q{quarter}" / f"{month_file}.md"

            if not file_path.exists():
                return f"错误: 找不到任务文件 {file_path}"

            writer = MarkdownWriter(file_path)
            success = writer.delete_task(task_id)

            if success:
                return f"✅ 已删除任务: {task_ref_display}"
            else:
                return f"错误: 删除任务失败，可能找不到该任务"
        else:
            return f"错误: 无效的任务引用格式: {task_ref} (需要5部分)"
    except Exception as e:
        return f"错误: {str(e)}"
