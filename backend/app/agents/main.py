"""Interface-Agent Plan and Resolve Agent"""

from pathlib import Path
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[3]))

from backend.app.agents.runner import run_plan_execute

app = typer.Typer(help="Interface-Agent Plan and Resolve Agent")
console = Console()


@app.command()
def generate(
    input_file: Optional[str] = typer.Option(None, "--input", "-i", help="输入文件路径"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="是否流式输出"),
):
    if input_file:
        with open(input_file, "r", encoding="utf-8") as file:
            user_input = file.read()
    else:
        import sys

        user_input = sys.stdin.read()
    console.print("\n✨ 执行中...\n")
    run_plan_execute(console, user_input, stream)


@app.command()
def chat():
    console.print(
        Panel.fit(
            "[bold cyan]💬 交互式 Plan and Resolve[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print("\n[green]✓ 准备就绪，输入需求后回车（输入 quit 退出）[/green]\n")
    while True:
        user_input = typer.prompt("你")
        if user_input.lower() in ["quit", "exit", "q"]:
            break
        result = run_plan_execute(console, user_input, False)
        console.print(f"\n[bold]AI:[/bold]\n{result.get('display', '')}\n")


@app.command()
def plan_execute(
    input_file: Optional[str] = typer.Option(None, "--input", "-i", help="输入文件路径"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="是否流式输出"),
):
    if input_file:
        with open(input_file, "r", encoding="utf-8") as file:
            user_input = file.read()
    else:
        import sys

        user_input = sys.stdin.read()
    console.print("\n✨ 执行中...\n")
    result = run_plan_execute(console, user_input, stream)
    if not stream:
        console.print(result.get("display", ""))


if __name__ == "__main__":
    app()
