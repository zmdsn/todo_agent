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


@main.command("check-reminders")
@click.option("--config", "-c", "config_path", default="config.yaml", help="配置文件路径")
@click.option("--todo-root", "-t", default=None, help="Todo 根目录")
def check_reminders(config_path: str, todo_root: str | None):
    """检查并发送提醒通知。"""
    import asyncio
    from pathlib import Path
    from todo_mcp.reminder.engine import ReminderEngine
    from todo_mcp.reminder.checker import ReminderChecker
    from todo_mcp.reminder.rules import RuleManager
    from todo_mcp.reminder.config import load_reminder_config
    from todo_mcp.reminder.notifiers.cli import CliNotifier
    from todo_mcp.parser.reader import MarkdownReader

    config = load_reminder_config(config_path)

    if not config.enabled:
        click.echo("提醒功能未启用，请在 config.yaml 中设置 reminders.enabled: true")
        return

    rule_manager = RuleManager(rules=config.rules)
    checker = ReminderChecker()
    notifier = CliNotifier(enabled=True)

    engine = ReminderEngine(
        rule_manager=rule_manager,
        checker=checker,
        notifiers={"cli": notifier},
    )

    # Get tasks from todo directory
    root = Path(todo_root) if todo_root else Path.home() / "todo"
    tasks = _collect_tasks(root)

    if not tasks:
        click.echo("未找到任何任务")
        return

    click.echo(f"检查 {len(tasks)} 个任务...")

    async def run_check():
        notifications = await engine.check_and_notify(tasks)
        return notifications

    notifications = asyncio.run(run_check())

    if notifications:
        click.echo(f"已发送 {len(notifications)} 个提醒通知")
    else:
        click.echo("没有需要提醒的任务")


@main.command("reminder-daemon")
@click.option("--config", "-c", "config_path", default="config.yaml", help="配置文件路径")
@click.option("--todo-root", "-t", default=None, help="Todo 根目录")
@click.option("--interval", "-i", default=300, help="检查间隔（秒）")
def reminder_daemon(config_path: str, todo_root: str | None, interval: int):
    """启动提醒守护进程。"""
    import asyncio
    from pathlib import Path
    from todo_mcp.reminder.engine import ReminderEngine
    from todo_mcp.reminder.checker import ReminderChecker
    from todo_mcp.reminder.rules import RuleManager
    from todo_mcp.reminder.scheduler import ReminderScheduler
    from todo_mcp.reminder.config import load_reminder_config
    from todo_mcp.reminder.notifiers.cli import CliNotifier

    config = load_reminder_config(config_path)

    if not config.enabled:
        click.echo("提醒功能未启用")
        return

    rule_manager = RuleManager(rules=config.rules)
    checker = ReminderChecker()
    notifier = CliNotifier(enabled=True, sound=True)

    engine = ReminderEngine(
        rule_manager=rule_manager,
        checker=checker,
        notifiers={"cli": notifier},
    )

    root = Path(todo_root) if todo_root else Path.home() / "todo"

    def get_tasks():
        return _collect_tasks(root)

    scheduler = ReminderScheduler(
        engine=engine,
        monitor_interval=interval,
        get_tasks_callback=get_tasks
    )

    click.echo(f"启动提醒守护进程...")
    click.echo(f"   配置: {config_path}")
    click.echo(f"   Todo 目录: {root}")
    click.echo(f"   检查间隔: {interval} 秒")
    click.echo("   按 Ctrl+C 停止\n")

    async def run():
        try:
            # Start scheduler in background
            await scheduler.start()
        except asyncio.CancelledError:
            await scheduler.stop()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        click.echo("\n提醒守护进程已停止")


def _collect_tasks(root: Path) -> list[dict]:
    """Collect all tasks from markdown files in todo directory."""
    from todo_mcp.parser.reader import MarkdownReader
    from todo_mcp.models import TaskStatus

    tasks = []

    if not root.exists():
        return tasks

    # Find all markdown files
    for md_file in root.rglob("*.md"):
        reader = MarkdownReader(md_file)
        file_tasks = reader.read_tasks()

        for task in file_tasks:
            task_dict = {
                "id": task.id,
                "content": task.content,
                "completed": task.status == TaskStatus.COMPLETED,
                "location": task.location,
                "due_date": task.due_date,
                "priority": task.priority,
            }
            tasks.append(task_dict)

    return tasks


if __name__ == "__main__":
    main()
