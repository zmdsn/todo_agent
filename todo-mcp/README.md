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

### 在 Cherry Studio 中配置

1. 打开设置 → MCP 服务器
2. 点击「添加服务器」
3. 填写配置：
   - 服务器名称: `todo`
   - 类型: `STDIO`
   - 命令: `uv`
   - 参数: `run`, `todo-mcp` (每行一个)
   - 工作目录: `/your/path/to/todo-mcp`
4. 保存并重启

### 其他 MCP 客户端

参见 [docs/mcp-clients.md](./docs/mcp-clients.md) 获取 Claude Desktop、Cline、Windsurf、Continue 等客户端的详细配置说明。

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

# 运行 STDIO 服务器 (默认)
uv run todo-mcp

# 运行 HTTP 服务器
uv run todo-mcp --http --port 33333
```

### HTTP 传输模式

支持 streamable-http 传输模式，适用于需要 HTTP 接入的场景：

```bash
# 启动 HTTP 服务
uv run todo-mcp --http --port 33333 --host 127.0.0.1
```

服务启动后，MCP 端点为 `http://127.0.0.1:33333/mcp/`

**命令行参数：**
- `--http` - 使用 streamable-http 传输
- `--port <端口>` - 指定端口 (默认 8000)
- `--host <地址>` - 指定绑定地址 (默认 127.0.0.1)

### 智能提醒

todo-mcp 支持智能提醒功能，可以在任务即将到期、任务过多时主动提醒。

#### 配置

在 `config.yaml` 中启用提醒：

```yaml
reminders:
  enabled: true
  rules:
    - type: due_soon
      days_before: [3, 1]
      channels: [cli]
    - type: daily_brief
      time: "08:00"
      channels: [cli]
  channels:
    cli:
      enabled: true
      sound: false
    webhook:
      enabled: true
      endpoints:
        - name: "企业微信"
          url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
          template: "markdown"
```

#### CLI 命令

```bash
# 检查提醒
uv run todo-mcp check-reminders

# 启动守护进程
uv run todo-mcp reminder-daemon
```

#### 在对话中管理提醒

```
用户: 把到期提醒改成提前 5 天
Agent: 已将到期提醒调整为提前 5 天提醒

用户: 每周回顾推送到钉钉
Agent: 已为每周回顾添加钉钉推送渠道
```

## 许可证

MIT
