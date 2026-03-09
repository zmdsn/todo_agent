# todo-mcp 设计文档

## 概述

一个轻量级 MCP Server，用于管理基于 Markdown 的个人计划系统。

## 核心特性

- 11 个 MCP Tools 覆盖计划管理全流程
- 纯 Markdown 存储，无额外数据库
- 支持自然语言时间表达
- 时间粒度：年 → 季 → 月 → 周 → 日

## MCP Tools

### 基础管理

| Tool | 功能 | 参数 |
|------|------|------|
| `create_plan` | 创建计划 | period, year, quarter?, month? |
| `list_plans` | 列出计划 | time_expr |
| `add_task` | 添加任务 | content, time_expr, priority?, due_date? |
| `update_task` | 更新任务 | task_id, status?, content? |
| `delete_task` | 删除任务 | task_id |
| `move_task` | 移动任务 | task_id, target_time_expr |

### 进度追踪

| Tool | 功能 | 参数 |
|------|------|------|
| `get_progress` | 获取进度 | time_expr |
| `generate_report` | 生成报告 | time_expr, format? |

### 智能提醒

| Tool | 功能 | 参数 |
|------|------|------|
| `get_reminders` | 获取提醒 | days_ahead? |
| `analyze_status` | 分析状态 | time_expr? |

### 今日视图

| Tool | 功能 | 参数 |
|------|------|------|
| `get_today` | 今日概览 | 无 |

## 数据模型

### 时间层级解析

| 用户输入 | 解析结果 | 文件路径 |
|----------|----------|----------|
| "今年" / "2026" | 2026年 | `2026/2026.md` |
| "Q1" / "第一季度" | 2026 Q1 | `2026/Q1/Q1.md` |
| "本月" / "3月" | 2026年3月 | `2026/Q1/03-March.md` |
| "本周" | 当前周 | 在当月文件中定位周 section |
| "今天" / "3月9日" | 具体日期 | 在当月文件中定位日 section |

### Task 结构

```python
@dataclass
class Task:
    id: str          # 唯一标识，格式: {年}-{季}-{月}-{日}-{序号}
    content: str     # 任务内容
    status: str      # "pending" | "completed"
    due_date: str    # 可选，截止日期
    priority: str    # 可选，优先级
    location: str    # 文件路径
```

### 月度计划模板（含日级别）

```markdown
# March 月度计划

## 本月重点
1. [重点1]
2. [重点2]

## 任务清单

### 第一周 (3/1 - 3/7)

#### 3/1 周六
- [ ] [任务]

#### 3/2 周日
- [ ] [任务]

### 第二周 (3/8 - 3/14)

#### 3/8 周六
- [ ] [任务]

...
```

## 项目结构

```
todo-mcp/
├── pyproject.toml          # 项目配置（uv 管理）
├── src/
│   └── todo_mcp/
│       ├── __init__.py
│       ├── server.py       # MCP Server 入口
│       ├── tools/          # MCP Tools 实现
│       │   ├── __init__.py
│       │   ├── plan.py     # 计划管理 tools
│       │   ├── task.py     # 任务管理 tools
│       │   ├── progress.py # 进度追踪 tools
│       │   └── reminder.py # 智能提醒 tools
│       ├── parser/         # Markdown 解析
│       │   ├── __init__.py
│       │   ├── reader.py   # 读取解析
│       │   └── writer.py   # 写入更新
│       ├── models/         # 数据模型
│       │   ├── __init__.py
│       │   └── task.py
│       └── utils/          # 工具函数
│           ├── __init__.py
│           └── time.py     # 时间解析
└── tests/                  # 测试
    └── ...
```

## 依赖

- `mcp` - MCP Python SDK
- `pydantic` - 数据验证
- `python-dateutil` - 日期解析

## 错误处理

- 文件不存在时自动创建（create_plan 场景）
- 无效时间表达返回友好提示
- 任务 ID 不存在时返回明确错误
- 文件写入失败时保留原文件

## 配置

```yaml
todo_root: /home/zmdsn/todo  # 计划文件根目录
default_reminder_days: 3     # 默认提前提醒天数
```
