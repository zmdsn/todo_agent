# Todo Agent 智能提醒功能设计

> 日期: 2026-03-12

## 目标

为 Todo Agent 添加智能提醒功能，支持多种提醒类型、通知渠道和触发模式。

## 需求

- **提醒类型**：任务到期提醒、计划健康检查、智能时间建议
- **通知渠道**：对话内提醒、CLI 推送、Webhook 回调
- **触发模式**：被动触发 + 定时任务 + 持续监控
- **配置方式**：配置文件为基础 + 支持对话中动态调整

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Todo Agent                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   CLI 模式   │    │   HTTP 模式   │    │  Scheduler   │   │
│  │  (被动触发)  │    │  (被动触发)   │    │ (定时+监控)  │   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘   │
│         │                   │                   │            │
│         └───────────────────┼───────────────────┘            │
│                             ▼                                │
│                  ┌─────────────────────┐                     │
│                  │   Reminder Engine   │                     │
│                  │  ┌───────────────┐  │                     │
│                  │  │ Rule Manager  │  │  ← 配置 + 对话调整  │
│                  │  └───────┬───────┘  │                     │
│                  │          ▼          │                     │
│                  │  ┌───────────────┐  │                     │
│                  │  │   Checker     │  │  ← 检查提醒条件     │
│                  │  └───────┬───────┘  │                     │
│                  │          ▼          │                     │
│                  │  ┌───────────────┐  │                     │
│                  │  │  Dispatcher   │  │  ← 分发通知         │
│                  │  └───────────────┘  │                     │
│                  └──────────┬──────────┘                     │
│                             ▼                                │
│         ┌───────────────────┼───────────────────┐            │
│         ▼                   ▼                   ▼            │
│  ┌────────────┐     ┌────────────┐     ┌────────────┐       │
│  │  In-Chat   │     │    CLI     │     │  Webhook   │       │
│  │  Notifier  │     │  Notifier  │     │  Notifier  │       │
│  └────────────┘     └────────────┘     └────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### ReminderEngine

统一入口，协调检查和分发流程。

```python
class ReminderEngine:
    def __init__(self, config: ReminderConfig):
        self.rule_manager = RuleManager(config)
        self.checker = ReminderChecker()
        self.dispatcher = NotificationDispatcher(config.channels)

    async def check_and_notify(self, context: CheckContext) -> list[Notification]:
        """检查所有规则并发送通知"""
        rules = self.rule_manager.get_active_rules()
        notifications = []

        for rule in rules:
            if self.checker.should_trigger(rule, context):
                notification = self.checker.build_notification(rule, context)
                await self.dispatcher.dispatch(notification, rule.channels)
                notifications.append(notification)

        return notifications
```

### RuleManager

管理提醒规则，支持配置文件和运行时调整。

```python
class RuleManager:
    def __init__(self, config: ReminderConfig):
        self._rules: dict[str, ReminderRule] = {}
        self._load_from_config(config)

    def update_rule(self, rule_type: str, params: dict) -> None:
        """更新规则（来自对话或配置）"""
        pass

    def get_active_rules(self) -> list[ReminderRule]:
        """获取所有启用的规则"""
        pass
```

### ReminderScheduler

支持定时任务和持续监控两种模式。

```python
class ReminderScheduler:
    def __init__(self, engine: ReminderEngine):
        self.engine = engine
        self._running = False

    async def start(self):
        """启动调度器"""
        self._running = True
        # 定时任务：daily_brief, weekly_review
        asyncio.create_task(self._run_scheduled())
        # 持续监控：due_soon, overdue, overload, stale
        asyncio.create_task(self._run_monitor())

    async def _run_scheduled(self):
        """定时任务"""
        pass

    async def _run_monitor(self):
        """持续监控（默认每 5 分钟）"""
        pass
```

## 提醒规则

### 规则类型

| 类型 | 触发条件 | 说明 |
|------|----------|------|
| **due_soon** | 任务即将到期 | 截止前 N 天提醒 |
| **overdue** | 任务已逾期 | 定期提醒直到完成 |
| **overload** | 任务过多 | 单日/周任务超过阈值 |
| **stale** | 长期未更新 | 任务 N 天无进展 |
| **weekly_review** | 定期回顾 | 每周一生成周报 |
| **daily_brief** | 每日简报 | 每天早上推送今日重点 |

### 配置文件格式

```yaml
reminders:
  enabled: true

  rules:
    - type: due_soon
      days_before: [3, 1]
      channels: [chat, cli]

    - type: overdue
      interval_hours: 24
      channels: [chat, cli, webhook]

    - type: overload
      daily_threshold: 8
      weekly_threshold: 30
      channels: [chat]

    - type: weekly_review
      day: monday
      time: "09:00"
      channels: [cli, webhook]

    - type: daily_brief
      time: "08:00"
      channels: [cli]

  channels:
    cli:
      enabled: true
      sound: true

    webhook:
      enabled: true
      endpoints:
        - name: "企业微信"
          url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
          template: "markdown"
```

## 通知渠道

### 基类

```python
class BaseNotifier(ABC):
    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """发送通知，返回是否成功"""
        pass
```

### CLI Notifier

使用系统通知工具：
- Linux: `notify-send`
- macOS: `terminal-notifier`
- 回退: 终端打印

```python
class CliNotifier(BaseNotifier):
    async def send(self, notification: Notification) -> bool:
        # 检测平台并调用对应工具
        pass
```

### Webhook Notifier

支持多种模板格式：Markdown、Text、JSON

```python
class WebhookNotifier(BaseNotifier):
    async def send(self, notification: Notification) -> bool:
        # POST 到配置的 URL
        pass
```

## Agent 工具

新增以下工具支持对话中管理提醒：

```python
@tool
def check_reminders() -> list[dict]:
    """检查当前所有待提醒事项"""

@tool
def update_reminder_rule(rule_type: str, action: str, params: dict) -> str:
    """更新提醒规则配置"""

@tool
def add_webhook(name: str, url: str, template: str = "markdown") -> str:
    """添加新的 Webhook 通知渠道"""

@tool
def test_notification(channel: str) -> bool:
    """测试通知渠道是否正常工作"""
```

### 对话示例

```
用户: 把到期提醒改成提前 5 天
Agent: 已将到期提醒调整为提前 5 天提醒

用户: 每周回顾推送到钉钉
Agent: 已为每周回顾添加钉钉推送渠道

用户: 测试一下企业微信通知
Agent: 已发送测试通知到企业微信，请检查是否收到
```

## 通知消息格式

```python
@dataclass
class Notification:
    title: str           # "📅 任务即将到期"
    level: str           # "info" | "warning" | "urgent"
    content: str         # 详细内容
    actions: list[str]   # 可选操作
    metadata: dict       # 关联数据
```

### 示例输出

```
📅 今日简报 (2026-03-12)

🎯 今日重点 (3 项)
• 完成周报撰写
• 审核设计文档
• 团队周会

⚠️ 注意事项
• 2 个任务将在 3 天内到期
• 本周已完成 12/20 个任务

💡 建议
考虑优先处理「审核设计文档」，截止日期为明天
```

## 项目结构

```
todo-mcp/
├── src/todo_mcp/
│   ├── reminder/              # 新增
│   │   ├── __init__.py
│   │   ├── engine.py          # ReminderEngine
│   │   ├── scheduler.py       # ReminderScheduler
│   │   ├── checker.py         # ReminderChecker
│   │   ├── rules.py           # RuleManager
│   │   ├── models.py          # Notification 等数据模型
│   │   └── notifiers/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── cli.py
│   │       └── webhook.py
│   ├── agent/                 # 更新
│   │   └── tools.py           # 添加提醒相关工具
│   └── ...
└── config.yaml                # 更新：添加 reminders 配置
```

## 与现有服务集成

### HTTP 服务启动调度器

```python
# src/todo_mcp/api/server.py

@app.on_event("startup")
async def startup():
    if config.reminders.enabled:
        scheduler = ReminderScheduler(engine)
        await scheduler.start()
        app.state.scheduler = scheduler
```

### CLI 命令

```bash
# 启动服务时启用调度器
todo-agent serve --with-scheduler

# 独立运行调度器
todo-agent reminder-daemon

# 手动检查提醒
todo-agent check-reminders
```

## 依赖

无需新增外部依赖，使用现有：
- `asyncio` - 异步调度
- `httpx` - Webhook 请求（已有）
