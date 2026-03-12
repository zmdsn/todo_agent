# MCP 客户端配置文档设计

> 日期: 2026-03-10

## 目标

为 todo-mcp 添加多客户端配置文档，使用户能够在各种 MCP 客户端中使用 todo-mcp 服务。

## 目标客户端

1. **Cherry Studio** (重点)
2. Claude Desktop
3. Cline (VS Code)
4. Windsurf
5. Continue

## 文件结构

```
todo-mcp/
├── README.md              # 更新：添加指向详细文档的链接
└── docs/
    └── mcp-clients.md     # 新建：各客户端配置指南
```

## 通用配置参数

所有客户端使用相同的核心配置：

```
命令: uv
参数: run, todo-mcp
工作目录: /path/to/todo-mcp
```

## 各客户端配置详情

### Cherry Studio

配置路径: 设置 → MCP 服务器 → 添加服务器

| 字段 | 值 |
|------|-----|
| 服务器名称 | todo |
| 类型 | STDIO |
| 命令 | uv |
| 参数 | run, todo-mcp |
| 工作目录 | /path/to/todo-mcp |

### Claude Desktop

配置文件: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

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

### Cline (VS Code)

配置文件: VS Code settings 或项目 `.clinerules`

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

### Windsurf

配置文件: `~/.codeium/windsurf/mcp_config.json`

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

### Continue

配置文件: `~/.continue/config.json`

```json
{
  "experimental": {
    "mcpServers": {
      "todo": {
        "command": "uv",
        "args": ["run", "todo-mcp"],
        "cwd": "/path/to/todo-mcp"
      }
    }
  }
}
```

## README 更新

在"使用"章节后添加：

```markdown
### 其他 MCP 客户端

参见 [docs/mcp-clients.md](./docs/mcp-clients.md) 获取 Cherry Studio、Claude Desktop、Cline、Windsurf、Continue 等客户端的配置说明。
```

## 验证方式

配置完成后，用户可通过以下方式验证：

1. 重启客户端
2. 在对话中询问"今天有什么任务"或"添加任务"
3. 确认 AI 能够调用 todo-mcp 的工具

## 常见问题

1. **服务启动失败** - 检查 uv 是否已安装，工作目录路径是否正确
2. **找不到工具** - 确认模型支持 Function Calling
3. **权限问题** - 确保配置文件中的路径有读取权限
