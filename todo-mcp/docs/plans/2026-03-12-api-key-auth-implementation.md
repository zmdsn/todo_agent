# API Key Authentication Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add API key authentication to protect `/v1/*` OpenAI-compatible endpoints.

**Architecture:** Use FastAPI's `Depends` with `HTTPBearer` to validate `Authorization: Bearer <key>` header. API key is configured via CLI flag or environment variable. When not configured, no authentication is required (backward compatible).

**Tech Stack:** FastAPI, HTTPBearer, Click CLI

---

## Task 1: API Key Verification Function

**Files:**
- Modify: `src/todo_mcp/api/openai_compat.py`
- Modify: `tests/test_openai_compat.py`

**Step 1: Write the failing tests**

Add to `tests/test_openai_compat.py`:

```python
class TestApiKeyAuthentication:
    """Test API key authentication for /v1/* endpoints."""

    @pytest.fixture
    def protected_client(self):
        """Create test client with API key configured."""
        from fastapi import FastAPI
        from todo_mcp.api.openai_compat import router, set_server_api_key

        set_server_api_key("test-secret-key")
        app = FastAPI()
        app.include_router(router)

        from fastapi.testclient import TestClient
        client = TestClient(app)
        yield client

        # Cleanup
        set_server_api_key(None)

    def test_no_auth_when_no_key_configured(self, client):
        """Test that requests work when no API key is configured."""
        # client fixture has no API key configured
        response = client.get("/v1/models")
        assert response.status_code == 200

    def test_reject_request_without_auth_header(self, protected_client):
        """Test 401 when API key is required but not provided."""
        response = protected_client.get("/v1/models")
        assert response.status_code == 401
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "invalid_api_key"

    def test_reject_request_with_wrong_key(self, protected_client):
        """Test 401 when wrong API key is provided."""
        response = protected_client.get(
            "/v1/models",
            headers={"Authorization": "Bearer wrong-key"}
        )
        assert response.status_code == 401

    def test_accept_request_with_correct_key(self, protected_client):
        """Test 200 when correct API key is provided."""
        response = protected_client.get(
            "/v1/models",
            headers={"Authorization": "Bearer test-secret-key"}
        )
        assert response.status_code == 200

    def test_protect_chat_completions(self, protected_client):
        """Test chat completions endpoint requires API key."""
        with patch("todo_mcp.api.openai_compat.get_agent") as mock_get:
            mock_get.return_value = MagicMock()

            with patch("todo_mcp.api.openai_compat.run_agent") as mock_run:
                mock_run.return_value = "响应"

                response = protected_client.post(
                    "/v1/chat/completions",
                    json={"model": "todo-agent", "messages": [{"role": "user", "content": "测试"}]},
                    headers={"Authorization": "Bearer test-secret-key"}
                )

        assert response.status_code == 200

    def test_protect_get_model(self, protected_client):
        """Test get model endpoint requires API key."""
        response = protected_client.get(
            "/v1/models/todo-agent",
            headers={"Authorization": "Bearer test-secret-key"}
        )
        assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_openai_compat.py::TestApiKeyAuthentication -v`
Expected: FAIL with AttributeError (set_server_api_key not defined)

**Step 3: Write minimal implementation**

Add to `src/todo_mcp/api/openai_compat.py` (after imports, before router):

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

# Server API key for authentication
_server_api_key: Optional[str] = None

security = HTTPBearer(auto_error=False)


def set_server_api_key(key: Optional[str]) -> None:
    """Set the server API key for authentication."""
    global _server_api_key
    _server_api_key = key


async def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """Verify API key from Authorization header."""
    # No key configured = no authentication required
    if _server_api_key is None:
        return "anonymous"

    # Key configured but no credentials provided
    if credentials is None:
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

    # Verify the key matches
    if credentials.credentials != _server_api_key:
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

Update endpoints to use the dependency:

```python
@router.get("/models", dependencies=[Depends(verify_api_key)])
async def list_models() -> dict:
    ...

@router.get("/models/{model_id}", dependencies=[Depends(verify_api_key)])
async def get_model(model_id: str) -> dict:
    ...

@router.post("/chat/completions", response_model=OpenAIChatResponse, dependencies=[Depends(verify_api_key)])
async def chat_completions(request: OpenAIChatRequest) -> OpenAIChatResponse:
    ...
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_openai_compat.py::TestApiKeyAuthentication -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/api/openai_compat.py tests/test_openai_compat.py
git commit -m "feat(api): add API key authentication for /v1/* endpoints"
```

---

## Task 2: CLI Flag and Environment Variable

**Files:**
- Modify: `src/todo_mcp/cli/main.py`
- Modify: `src/todo_mcp/api/server.py`
- Modify: `tests/test_openai_compat.py`

**Step 1: Write the failing tests**

Add to `tests/test_openai_compat.py`:

```python
import os


class TestServerApiKeyConfiguration:
    """Test server API key configuration from CLI and env."""

    def test_create_app_with_server_api_key(self):
        """Test create_app accepts server_api_key parameter."""
        from todo_mcp.api.server import create_app
        from todo_mcp.api.openai_compat import _server_api_key

        app = create_app(server_api_key="cli-secret-key")

        # The key should be set in openai_compat module
        from todo_mcp.api import openai_compat
        assert openai_compat._server_api_key == "cli-secret-key"

        # Cleanup
        openai_compat.set_server_api_key(None)

    def test_env_var_api_key(self, monkeypatch):
        """Test TODO_API_KEY environment variable is read."""
        monkeypatch.setenv("TODO_API_KEY", "env-secret-key")

        from todo_mcp.api.server import create_app
        from todo_mcp.api import openai_compat

        app = create_app()

        assert openai_compat._server_api_key == "env-secret-key"

        # Cleanup
        openai_compat.set_server_api_key(None)
        monkeypatch.delenv("TODO_API_KEY")
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_openai_compat.py::TestServerApiKeyConfiguration -v`
Expected: FAIL (server_api_key parameter not accepted)

**Step 3: Write minimal implementation**

Modify `src/todo_mcp/api/server.py`:

```python
# Update import
from todo_mcp.api.openai_compat import router as openai_router, set_config as set_openai_config, set_server_api_key
import os


def create_app(
    model: str = "qwen2.5",
    base_url: str = "http://localhost:11434/v1",
    temperature: float = 0.7,
    api_key: str = "dummy",
    server_api_key: Optional[str] = None
):
    """创建 FastAPI 应用。"""
    global _config
    _config = {
        "model": model,
        "base_url": base_url,
        "temperature": temperature,
        "api_key": api_key
    }

    # Set server API key (from param or env var)
    effective_key = server_api_key or os.environ.get("TODO_API_KEY")
    if effective_key:
        set_server_api_key(effective_key)

    # 同步配置到 OpenAI 兼容层
    set_openai_config(base_url, model, temperature, api_key)

    # ... rest of function unchanged
```

Modify `src/todo_mcp/cli/main.py`:

```python
@main.command()
@click.option("--port", "-p", default=8080, help="服务端口")
@click.option("--host", "-h", default="127.0.0.1", help="绑定地址")
@click.option("--model", "-m", default="qwen2.5", help="LLM 模型名称")
@click.option("--base-url", "-u", default="http://localhost:11434/v1", help="LLM API 地址")
@click.option("--api-key", "-k", default="dummy", help="LLM API 密钥")
@click.option("--server-api-key", "-s", default=None, help="服务 API 密钥（保护 /v1/* 端点）")
def serve(port: int, host: str, model: str, base_url: str, api_key: str, server_api_key: str | None):
    """启动 HTTP API 服务。"""
    import uvicorn
    from todo_mcp.api.server import create_app

    click.echo(f"🚀 启动 API 服务...")
    click.echo(f"   地址: http://{host}:{port}")
    click.echo(f"   模型: {model}")
    click.echo(f"   API: {base_url}")
    if server_api_key:
        click.echo(f"   认证: 已启用")

    app = create_app(model=model, base_url=base_url, api_key=api_key, server_api_key=server_api_key)
    uvicorn.run(app, host=host, port=port)
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_openai_compat.py::TestServerApiKeyConfiguration -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/cli/main.py src/todo_mcp/api/server.py tests/test_openai_compat.py
git commit -m "feat(cli): add --server-api-key option for API authentication"
```

---

## Task 3: Run All Tests

**Step 1: Run full test suite**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest -v`

Expected: All tests PASS

**Step 2: Fix any failures**

If any tests fail, debug and fix.

**Step 3: Final commit (if needed)**

```bash
git add -A
git commit -m "feat(api): complete API key authentication implementation"
```

---

## Summary

| Task | Component | Files |
|------|-----------|-------|
| 1 | API Key Verification | `api/openai_compat.py` |
| 2 | CLI & Env Config | `cli/main.py`, `api/server.py` |
| 3 | Final Testing | - |
