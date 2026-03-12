# API Key 验证设计

> 日期: 2026-03-12

## 目标

为 OpenAI 兼容 API 添加 API key 验证，保护 `/v1/*` 端点不被未授权访问。

## 需求

- 启动时指定单个 API key
- 使用标准 Authorization Header 传递
- 仅保护 `/v1/*` 端点
- 未设置 key 时不进行验证（向后兼容）

## 配置方式

| 来源 | 参数 | 优先级 |
|------|------|--------|
| CLI 参数 | `--server-api-key` | 高 |
| 环境变量 | `TODO_API_KEY` | 低 |
| 默认值 | 无（不验证） | - |

## 验证逻辑

**请求格式：**
```
Authorization: Bearer <api-key>
```

**验证范围：**
- `/v1/chat/completions` - 需要验证
- `/v1/models` - 需要验证
- `/v1/models/{model_id}` - 需要验证
- `/chat`、`/tools` 等 - 不需要验证

**错误响应：**
```json
{
  "error": {
    "message": "Invalid API key",
    "type": "invalid_request_error",
    "code": "invalid_api_key"
  }
}
```
HTTP 状态码：401 Unauthorized

## 技术实现

使用 FastAPI 的 `Depends` + `HTTPBearer` 进行验证：

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException

security = HTTPBearer(auto_error=False)

async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    api_key: str | None = None  # 从配置注入
) -> str:
    # 未配置 server_api_key 时跳过验证
    if not api_key:
        return "anonymous"

    if not credentials or credentials.credentials != api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Invalid API key",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key"
                }
            }
        )

    return credentials.credentials
```

## 文件变更

| 文件 | 变更 |
|------|------|
| `src/todo_mcp/api/openai_compat.py` | 添加验证依赖 |
| `src/todo_mcp/api/server.py` | 传递 server_api_key 配置 |
| `src/todo_mcp/cli/main.py` | 添加 `--server-api-key` 参数 |

## 使用示例

**启动服务（带验证）：**
```bash
todo-agent serve --server-api-key my-secret-key
# 或
TODO_API_KEY=my-secret-key todo-agent serve
```

**调用 API：**
```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer my-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"model": "todo-agent", "messages": [{"role": "user", "content": "你好"}]}'
```

**启动服务（无验证）：**
```bash
todo-agent serve
# 所有请求都可以访问
```
