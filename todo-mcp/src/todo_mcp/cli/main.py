# todo-mcp/src/todo_mcp/cli/main.py
"""CLI interface for todo agent."""
import click
import sys
from pathlib import Path

from todo_mcp.agent import create_todo_agent, run_agent, session_manager
from todo_mcp.models import Config


def load_config() -> Config:
    """加载配置。"""
    # 查找配置文件
    config_paths = [
        Path.cwd() / "config.yaml",
        Path.home() / ".config" / "todo-agent" / "config.yaml",
    ]

    for path in config_paths:
        if path.exists():
            import yaml
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            return Config(**data.get("todo", {}))

    return Config()


@click.group()
@click.version_option(version="0.2.0")
def main():
    """Todo Agent - 个人计划管理智能助手。"""
    pass


@main.command()
@click.option("--model", "-m", default="qwen2.5", help="LLM 模型名称")
@click.option("--base-url", "-u", default="http://localhost:11434/v1", help="LLM API 地址")
@click.option("--temperature", "-t", default=0.7, help="温度参数")
def chat(model: str, base_url: str, temperature: float):
    """启动交互式对话。"""
    click.echo(f"🤖 Todo Agent 启动中...")
    click.echo(f"   模型: {model}")
    click.echo(f"   API: {base_url}")
    click.echo(f"   输入 'quit' 或 'exit' 退出\n")

    try:
        agent = create_todo_agent(
            base_url=base_url,
            model=model,
            temperature=temperature
        )
    except Exception as e:
        click.echo(f"❌ 无法连接到 LLM: {e}", err=True)
        sys.exit(1)

    click.echo("💬 开始对话吧！\n")

    while True:
        try:
            user_input = click.prompt("你", type=str).strip()
        except (KeyboardInterrupt, EOFError):
            click.echo("\n👋 再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "q"]:
            click.echo("👋 再见！")
            break

        if user_input.lower() in ["clear", "reset"]:
            session_manager.clear_session("cli")
            click.echo("🔄 会话已重置\n")
            continue

        try:
            response = run_agent(agent, user_input, session_manager, "cli")
            click.echo(f"\n🤖 {response}\n")
        except Exception as e:
            click.echo(f"❌ 错误: {e}\n")


@main.command()
@click.option("--port", "-p", default=8080, help="服务端口")
@click.option("--host", "-h", default="127.0.0.1", help="绑定地址")
@click.option("--model", "-m", default="qwen2.5", help="LLM 模型名称")
@click.option("--base-url", "-u", default="http://localhost:11434/v1", help="LLM API 地址")
def serve(port: int, host: str, model: str, base_url: str):
    """启动 HTTP API 服务。"""
    import uvicorn
    from todo_mcp.api.server import create_app

    click.echo(f"🚀 启动 API 服务...")
    click.echo(f"   地址: http://{host}:{port}")
    click.echo(f"   模型: {model}")
    click.echo(f"   API: {base_url}")

    app = create_app(model=model, base_url=base_url)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
