"""Interface-Agent Plan and Resolve Agent"""

from pathlib import Path
import sys
from typing import Optional
from rich.console import Console
from rich.panel import Panel

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[3]))

from backend.app.agents.plan_resolve_runner import run_plan_and_resolve
from backend.app.agents.llm import get_llm

console = Console()


def generate(
    input_file: Optional[str] = None,
    stream: bool = True,
):
    if input_file:
        with open(input_file, "r", encoding="utf-8") as file:
            user_input = file.read()
    else:
        import sys

        user_input = sys.stdin.read()
    console.print("\n✨ 执行中...\n")
    run_plan_and_resolve(console, user_input, stream)


def chat():
    console.print(
        Panel.fit(
            "[bold cyan]💬 交互式 Plan and Resolve[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print("\n[green]✓ 准备就绪，输入需求后回车（输入 quit 退出）[/green]\n")
    while True:
        user_input = input("你: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            break
        result = run_plan_and_resolve(console, user_input, False)
        console.print(f"\n[bold]AI:[/bold]\n{result.get('display', '')}\n")


def plan_execute(
    input_file: Optional[str] = None,
    stream: bool = True,
):
    if input_file:
        with open(input_file, "r", encoding="utf-8") as file:
            user_input = file.read()
    else:
        import sys

        user_input = sys.stdin.read()
    console.print("\n✨ 执行中...\n")
    result = run_plan_and_resolve(console, user_input, stream)
    if not stream:
        console.print(result.get("display", ""))


def stream_test(
    prompt: str = "详细说明下现在大模型的上下文工程",
):
    llm = get_llm(console)
    if not llm:
        raise RuntimeError("LLM 初始化失败")
    for attempt in range(2):
        try:
            for chunk in llm.stream(prompt):
                content = getattr(chunk, "content", "")
                if content:
                    text = content if isinstance(content, str) else str(content)
                    sys.stdout.write(text)
                    sys.stdout.flush()
            sys.stdout.write("\n")
            sys.stdout.flush()
            return
        except Exception as exc:
            if attempt == 0:
                sys.stdout.write(f"\n\n⚠️ 流式连接中断，正在重试：{exc}\n")
                sys.stdout.flush()
                llm = get_llm(console)
                if not llm:
                    raise RuntimeError("LLM 重试初始化失败")
                continue
            raise


if __name__ == "__main__":
    stream_test("详细说明下现在大模型的上下文工程")
