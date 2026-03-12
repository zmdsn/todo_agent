from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List


class TaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class Task(BaseModel):
    id: str = Field(..., description="唯一标识，格式: {年}-{季}-{月}-{日}-{序号}")
    content: str = Field(..., description="任务内容")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    location: str = Field(..., description="文件路径")
    due_date: Optional[str] = Field(None, description="截止日期")
    priority: Optional[str] = Field(None, description="优先级: high/medium/low")

    # 任务拆分相关字段
    parent_id: Optional[str] = Field(None, description="父任务ID")
    estimated_minutes: Optional[int] = Field(None, description="预估时间（分钟）")
    subtask_ids: List[str] = Field(default_factory=list, description="子任务ID列表")
