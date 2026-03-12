# src/todo_mcp/utils/estimator.py
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
