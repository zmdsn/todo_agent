# Todo Agent

个人计划管理智能助手，基于 MCP 和 OpenAI 兼容 API。

## 项目结构

```
todo/
├── todo-mcp/          # MCP Server 和 OpenAI API 实现
│   ├── src/todo_mcp/  # 核心代码
│   └── tests/         # 测试
├── 2026/              # 计划数据 (gitignored)
└── config.yaml        # 配置文件
```

## 快速开始

```bash
cd todo-mcp
uv sync
uv run todo-agent serve --port 6501
```

详细文档请参见 [todo-mcp/README.md](./todo-mcp/README.md)。
