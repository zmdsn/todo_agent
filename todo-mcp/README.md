# todo-mcp

一个用于管理个人计划的 MCP Server。

## 安装

```bash
# 使用 uv 安装
cd todo-mcp
uv sync
```

## 配置

创建 `config.yaml` 文件:

```yaml
todo_root: ~/todo  # 计划文件根目录
default_reminder_days: 3  # 默认提前提醒天数
```

## 使用

### 在 Claude Code 中配置

在 Claude Code 的配置文件中添加:

```json
{
  "mcpServers": {
    "todo": {
      "command": "uv",
      "args": ["run", "todo-mcp"],
      "cwd": "/path/to/todo-mcp"
    }
  }
}
```

### 可用工具

- `add_task` - 添加任务
- `update_task` - 更新任务
- `delete_task` - 删除任务
- `get_today` - 获取今日概览
- `get_progress` - 获取进度
- `list_plans` - 列出计划
- `create_plan` - 创建计划
- `get_reminders` - 获取提醒
- `analyze_status` - 分析状态
- `generate_report` - 生成报告
- `move_task` - 移动任务

## 示例

添加任务:
```
add_task(content="完成报告", time_expr="今天")
```

获取今日概览:
```
get_today()
```

## 开发

```bash
# 运行测试
uv run pytest

# 运行服务器
uv run todo-mcp
```

## 许可证

MIT
