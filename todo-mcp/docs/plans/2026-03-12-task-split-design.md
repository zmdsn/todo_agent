# 任务拆分与时间预估功能设计

## 概述

为 todo-mcp 添加智能任务拆分和时间预估功能，帮助用户将复杂任务分解为可管理的子任务，并提供合理的时间预估。

## 需求总结

| 方面 | 决策 |
|------|------|
| 触发方式 | 添加任务时提示 + 单独命令 |
| 拆分粒度 | 智能体自动判断 |
| 时间预估 | 智能体估算 + 用户确认 |
| 存储方式 | 父子任务关系 |
| 触发条件 | 预估超过阈值 + 主动请求 |
| 估算因素 | 任务内容 + 优先级 |

## 技术方案

**纯 LLM 驱动**：利用现有 Agent 的 LLM 能力，通过精心设计的 prompt 让智能体理解任务拆分逻辑。

## 数据模型

### 任务模型扩展

```python
class Task:
    id: str
    content: str
    status: TaskStatus
    location: str
    priority: Optional[str]

    # 新增字段
    parent_id: Optional[str] = None           # 父任务ID
    estimated_minutes: Optional[int] = None   # 预估时间（分钟）
    subtask_ids: List[str] = []               # 子任务ID列表
```

### Markdown 格式扩展

```markdown
## 12日

- [ ] 完成项目报告 (预估: 4h)
  - [ ] 收集数据 (预估: 1h)
  - [ ] 撰写初稿 (预估: 2h)
  - [ ] 审核修改 (预估: 1h)
```

- 父子关系通过缩进（2空格）表示
- 预估时间格式：`(预估: Xh)` 或 `(预估: Xm)`
- 完成所有子任务时，自动将父任务标记为完成

## 工具设计

### 新增工具

#### 1. `estimate_task` - 预估任务时间

```python
@tool
def estimate_task(content: str, priority: Optional[str] = None) -> dict:
    """预估任务完成时间。

    Args:
        content: 任务内容
        priority: 优先级 (high/medium/low)

    Returns:
        {
            "estimated_minutes": 120,
            "should_split": True,
            "reason": "预估时间超过2小时"
        }
    """
```

#### 2. `split_task` - 拆分任务

```python
@tool
def split_task(
    content: str,
    priority: Optional[str] = None,
    target_minutes: int = 60
) -> dict:
    """拆分任务为子任务。

    Returns:
        {
            "subtasks": [
                {"content": "收集数据", "estimated_minutes": 30},
                {"content": "撰写初稿", "estimated_minutes": 60},
            ],
            "total_minutes": 150
        }
    """
```

#### 3. `add_task_with_split` - 添加任务（支持拆分）

```python
@tool
def add_task_with_split(
    content: str,
    time_expr: str,
    priority: Optional[str] = None,
    auto_split: bool = True
) -> str:
    """添加任务，自动检测是否需要拆分。

    流程：
    1. 预估时间
    2. 如果超过阈值且 auto_split=True，提示用户确认拆分
    3. 添加任务（可能包含子任务）
    """
```

### 修改现有工具

- `update_task`：增加逻辑 - 当子任务全部完成时，自动标记父任务完成

## Agent 提示词

```python
SYSTEM_PROMPT = """你是一个个人计划管理助手，帮助用户管理日常任务和计划。

你可以帮助用户：
- 添加、查看、更新任务
- 分析任务完成进度
- 提供智能安排建议
- 拆分复杂任务并预估完成时间

## 任务拆分规则

当用户添加任务时：
1. 先预估任务完成时间
2. 如果预估超过 2 小时，询问用户是否需要拆分
3. 拆分时，每个子任务控制在 30-60 分钟

## 时间预估规则

- high 优先级：需要更仔细，预估时间 x1.2
- low 优先级：可以快速完成，预估时间 x0.8
- 复杂任务（涉及多个步骤）：按步骤分别估算后求和

## 拆分命令

用户可以说：
- "帮我把 [任务] 拆分一下"
- "拆分 [任务ID]"
- "这个任务太大了，拆小一点"

当前日期: {current_date}
"""
```

## 交互流程示例

```
用户: 添加任务：完成季度报告，明天

Agent:
预估这个任务需要约 4 小时完成，超过了建议的 2 小时阈值。
是否需要拆分为更小的子任务？

[1] 是，帮我拆分
[2] 不用，直接添加

用户: 1

Agent:
已将「完成季度报告」拆分为以下子任务：
- 收集数据 (预估: 1h)
- 整理分析 (预估: 1.5h)
- 撰写报告 (预估: 1h)
- 审核修改 (预估: 0.5h)

总计: 4h

已添加到明天的计划中！
```

## 文件结构

```
todo-mcp/src/todo_mcp/
├── models/
│   └── task.py          # 扩展 Task 模型
├── parser/
│   ├── reader.py        # 支持：读取层级任务
│   └── writer.py        # 支持：写入层级任务
├── agent/
│   ├── tools.py         # 新增：estimate_task, split_task, add_task_with_split
│   └── prompts.py       # 扩展系统提示词
└── utils/
    └── estimator.py     # 新增：时间预估逻辑
```

## 配置扩展

```yaml
# config.yaml 新增
task_split:
  threshold_minutes: 120       # 超过此时间提示拆分
  target_subtask_minutes: 60   # 子任务目标时长
  auto_complete_parent: true   # 子任务全完成时自动完成父任务
```

## 实现要点

1. **时间预估阈值**：默认 2 小时（120 分钟），可配置
2. **子任务目标时长**：默认 30-60 分钟
3. **自动完成父任务**：在 `update_task` 中检测并自动标记
4. **Markdown 解析**：通过缩进层级识别父子关系
