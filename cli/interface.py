"""
CLI Interface — Person 1
Terminal REPL with Typer and Rich. Displays tool execution logs and agent responses.
"""
import json
from typing import Any, Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt

console = Console()

QUIT_COMMANDS = {"exit", "quit", "q"}
MODE_COMMANDS = {"set mode safe", "set mode auto"}


def display_tool_log(tool_name: str, message: str) -> None:
    """Display a simple tool log line (legacy / internal use)."""
    console.print(f"  [bold cyan][TOOL][/bold cyan] [yellow]{tool_name}[/yellow] — {message}")


def display_tool_call(tool_name: str, arguments: dict, result: dict) -> None:
    """
    Display a tool call visibly in the terminal so it's clear what the agent is doing.
    Shows the tool name, arguments, and whether it succeeded or failed.
    """
    # Format arguments compactly (single line, truncated if long)
    args_str = json.dumps(arguments)
    if len(args_str) > 80:
        args_str = args_str[:77] + "..."

    status = result.get("status", "unknown")
    if status == "success":
        status_markup = "[bold green]✓[/bold green]"
    else:
        status_markup = "[bold red]✗[/bold red]"

    console.print(
        f"  [bold cyan]⚙ Tool:[/bold cyan] [yellow]{tool_name}[/yellow]  "
        f"[dim]{args_str}[/dim]  {status_markup}"
    )


def display_response(response: str) -> None:
    """Display the agent's final response in a styled panel."""
    console.print(Panel(response, title="[bold green]Agent[/bold green]", border_style="green"))


def begin_stream() -> None:
    """Print the streaming header before chunks arrive."""
    console.print("[bold green]╭─── Agent ───────────────────────────────────────────────────────╮[/bold green]")
    console.print("[bold green]│[/bold green] ", end="")


def stream_chunk(chunk: str) -> None:
    """Print a single streamed chunk inline, handling newlines cleanly."""
    # Replace newlines so subsequent lines get the border prefix
    formatted = chunk.replace("\n", "\n[bold green]│[/bold green] ")
    console.print(formatted, end="", highlight=False)


def end_stream() -> None:
    """Print the streaming footer after all chunks arrive."""
    console.print()
    console.print("[bold green]╰─────────────────────────────────────────────────────────────────╯[/bold green]")


def display_usage(usage: dict) -> None:
    """Display token usage stats in a subtle dim line below the response."""
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    total = usage.get("total_tokens", 0)
    console.print(
        f"  [dim]↳ {total:,} tokens  "
        f"({prompt:,} prompt + {completion:,} completion)[/dim]"
    )


def display_error(message: str) -> None:
    """Display an error message."""
    console.print(f"[bold red][ERROR][/bold red] {message}")


def display_welcome(safe_mode: bool = False) -> None:
    """Display welcome banner including current execution mode."""
    mode_label = "[bold red]SAFE[/bold red]" if safe_mode else "[bold green]AUTO[/bold green]"
    console.print(
        Panel(
            "[bold]Vertex — AI Coding Assistant[/bold]\n"
            "Type your coding task and press Enter.\n"
            f"Execution mode: {mode_label}  "
            "[dim](type [bold]set mode safe[/bold] or [bold]set mode auto[/bold] to change)[/dim]\n"
            "Type [bold]exit[/bold] or [bold]quit[/bold] to stop.",
            border_style="blue",
        )
    )


def ask_execution_mode() -> bool:
    """
    Ask the user to choose safe or auto mode at startup.
    Returns True for safe mode, False for auto mode.
    """
    console.print()
    console.print(
        Panel(
            "[bold]Welcome to Vertex[/bold] — Your AI Coding Assistant\n\n"
            "[bold cyan]Choose an execution mode:[/bold cyan]\n\n"
            "  [bold green]auto[/bold green]  — Agent executes all tools automatically (fastest)\n"
            "  [bold red]safe[/bold red]  — Agent asks for your confirmation before writing or "
            "running shell commands",
            title="Setup",
            border_style="cyan",
        )
    )

    choice = Prompt.ask(
        "  Mode",
        choices=["auto", "safe"],
        default="auto",
    )

    safe_mode = choice == "safe"
    mode_label = "[bold red]SAFE MODE[/bold red]" if safe_mode else "[bold green]AUTO MODE[/bold green]"
    console.print(f"\n  {mode_label} enabled.")
    console.print(
        "  [dim]You can change this any time by typing "
        "[bold]set mode safe[/bold] or [bold]set mode auto[/bold][/dim]\n"
    )
    return safe_mode


def run_repl(
    agent_fn: Callable,
    executor: Optional[Any] = None,
    safe_mode: bool = False,
) -> None:
    """
    Run the main REPL loop.

    Args:
        agent_fn:  Callable(user_input, on_stream_chunk=None) -> str.
                   Accepts an optional streaming callback for live output.
        executor:  ToolExecutor instance — if provided, allows live mode switching.
        safe_mode: Initial execution mode (True = safe, False = auto).
    """
    display_welcome(safe_mode=safe_mode)

    while True:
        try:
            user_input = console.input("[bold blue]>[/bold blue] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() in QUIT_COMMANDS:
            console.print("[dim]Goodbye.[/dim]")
            break

        # Live mode switching
        cmd = user_input.lower()
        if cmd == "set mode safe":
            if executor:
                executor.set_safe_mode(True)
            console.print(
                "  [bold red]SAFE MODE[/bold red] enabled. "
                "[dim]Agent will ask for confirmation before write/shell commands.[/dim]"
            )
            continue
        if cmd == "set mode auto":
            if executor:
                executor.set_safe_mode(False)
            console.print(
                "  [bold green]AUTO MODE[/bold green] enabled. "
                "[dim]Agent will execute all tools automatically.[/dim]"
            )
            continue

        console.print("[dim]Thinking...[/dim]")
        try:
            # Track whether streaming started so we only call begin/end_stream once
            streaming_state = {"started": False}
            usage_holder: list = []

            def _on_stream_chunk(chunk: str) -> None:
                if not streaming_state["started"]:
                    begin_stream()
                    streaming_state["started"] = True
                stream_chunk(chunk)

            def _on_usage(usage: dict) -> None:
                usage_holder.append(usage)

            response = agent_fn(
                user_input,
                on_stream_chunk=_on_stream_chunk,
                on_usage=_on_usage,
            )

            if streaming_state["started"]:
                end_stream()
            else:
                # Provider doesn't support streaming — fall back to panel display
                display_response(response)

            if usage_holder:
                display_usage(usage_holder[0])
        except Exception as exc:
            display_error(str(exc))
