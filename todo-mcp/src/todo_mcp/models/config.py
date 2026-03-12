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
