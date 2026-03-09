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
