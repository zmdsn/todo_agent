# MCP 客户端配置文档实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 todo-mcp 添加多客户端配置文档，支持 Cherry Studio、Claude Desktop、Cline、Windsurf、Continue 等客户端。

**Architecture:** 创建独立的配置文档 `docs/mcp-clients.md`，在 README 中添加链接引用。各客户端使用统一的 STDIO 配置方式。

**Tech Stack:** Markdown 文档，MCP STDIO 协议

---

## Task 1: 创建 MCP 客户端配置文档

**Files:**
- Create: `todo-mcp/docs/mcp-clients.md`

**Step 1: 创建 docs 目录**

```bash
mkdir -p /home/zmdsn/todo/todo-mcp/docs
```

**Step 2: 创建 mcp-clients.md 文件**

创建文件 `todo-mcp/docs/mcp-clients.md`，内容如下：

```markdown
# MCP 客户端配置指南

本文档介绍如何在各种 MCP 客户端中配置 todo-mcp 服务。

## 通用配置参数

所有客户端使用相同的核心配置：

| 参数 | 值 |
|------|-----|
| 命令 | `uv` |
| 参数 | `run`, `todo-mcp` |
| 工作目录 | `/path/to/todo-mcp` (替换为你的实际路径) |

---

## Cherry Studio

1. 打开 Cherry Studio，点击左下角「设置」
2. 选择「MCP 服务器」
3. 点击右上角「添加服务器」
4. 填写以下信息：

| 字段 | 值 |
|------|-----|
| 服务器名称 | `todo` |
| 类型 | `STDIO` |
| 命令 | `uv` |
| 参数 | `run, todo-mcp` (每行一个参数) |
| 工作目录 | `/your/path/to/todo-mcp` |

5. 点击保存，等待服务启动

---

## Claude Desktop

### macOS

配置文件: `~/Library/Application Support/Claude/claude_desktop_config.json`

### Windows

配置文件: `%APPDATA%\Claude\claude_desktop_config.json`

### Linux

配置文件: `~/.config/Claude/claude_desktop_config.json`

### 配置内容

```json
{
  "mcpServers": {
    "todo": {
      "command": "uv",
      "args": ["run", "todo-mcp"],
      "cwd": "/your/path/to/todo-mcp"
    }
  }
}
```

---

## Cline (VS Code)

### 方式一: VS Code 设置

在 VS Code 的 `settings.json` 中添加：

```json
{
  "cline.mcpServers": {
    "todo": {
      "command": "uv",
      "args": ["run", "todo-mcp"],
      "cwd": "/your/path/to/todo-mcp"
    }
  }
}
```

### 方式二: 项目配置

在项目根目录创建 `.clinerules` 文件：

```json
{
  "mcpServers": {
    "todo": {
      "command": "uv",
      "args": ["run", "todo-mcp"],
      "cwd": "/your/path/to/todo-mcp"
    }
  }
}
```

---

## Windsurf

配置文件: `~/.codeium/windsurf/mcp_config.json`

```json
{
  "mcpServers": {
    "todo": {
      "command": "uv",
      "args": ["run", "todo-mcp"],
      "cwd": "/your/path/to/todo-mcp"
    }
  }
}
```

---

## Continue

配置文件: `~/.continue/config.json`

```json
{
  "experimental": {
    "mcpServers": {
      "todo": {
        "command": "uv",
        "args": ["run", "todo-mcp"],
        "cwd": "/your/path/to/todo-mcp"
      }
    }
  }
}
```

---

## 验证配置

配置完成后：

1. 重启客户端应用
2. 在对话中尝试：
   - "今天有什么任务？"
   - "帮我添加一个任务：完成报告"
3. 确认 AI 能够正确调用 todo-mcp 的工具

---

## 常见问题

### 服务启动失败

- 确认已安装 [uv](https://docs.astral.sh/uv/)
- 检查工作目录路径是否正确（使用绝对路径）
- 确认 todo-mcp 目录中存在 `pyproject.toml`

### 找不到工具

- 确认使用的模型支持 Function Calling / Tool Calling
- 推荐: Claude 3.5+, GPT-4, Gemini Pro

### 权限问题

- 确保配置文件中的路径有读取权限
- 确保 todo-mcp 目录中的文件可读写

## 可用工具

配置成功后，可使用以下工具：

| 工具 | 说明 |
|------|------|
| `add_task` | 添加任务 |
| `get_today` | 获取今日概览 |
| `update_task` | 更新任务状态 |
| `delete_task` | 删除任务 |
| `list_plans` | 列出计划 |
| `get_progress` | 获取进度 |
| `move_task` | 移动任务 |
| `get_reminders` | 获取提醒 |
| `analyze_status` | 分析状态 |
| `generate_report` | 生成报告 |
```

**Step 3: 验证文件创建**

```bash
cat /home/zmdsn/todo/todo-mcp/docs/mcp-clients.md | head -20
```

Expected: 显示文件前 20 行内容

---

## Task 2: 更新 README 添加链接

**Files:**
- Modify: `todo-mcp/README.md`

**Step 1: 读取当前 README**

Run: `cat /home/zmdsn/todo/todo-mcp/README.md`

**Step 2: 在「使用」章节后添加其他客户端链接**

在 `### 在 Claude Code 中配置` 章节之后，`### 可用工具` 之前，添加：

```markdown
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

```

**Step 3: 验证更新**

```bash
grep -A 5 "其他 MCP 客户端" /home/zmdsn/todo/todo-mcp/README.md
```

Expected: 显示新添加的内容

---

## Task 3: 提交更改

**Step 1: 查看更改状态**

```bash
cd /home/zmdsn/todo && git status
```

**Step 2: 暂存文件**

```bash
git add todo-mcp/docs/mcp-clients.md todo-mcp/README.md
```

**Step 3: 提交**

```bash
git commit -m "$(cat <<'EOF'
docs: add MCP client configuration guide

- Add docs/mcp-clients.md with configuration for Cherry Studio, Claude Desktop, Cline, Windsurf, Continue
- Update README.md with Cherry Studio instructions and link to detailed docs

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## 完成清单

- [ ] `docs/mcp-clients.md` 已创建
- [ ] `README.md` 已更新
- [ ] 更改已提交到 git
