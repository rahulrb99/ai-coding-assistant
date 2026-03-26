"""
CLI Interface — Person 1
Terminal REPL with Typer and Rich. Displays tool execution logs and agent responses.
"""
import json
import re
from pathlib import Path
from typing import Any, Callable, Optional

_PREFS_FILE = Path(".logs/preferences.json")

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt

console = Console()

QUIT_COMMANDS = {"exit", "quit", "q"}
MODE_COMMANDS = {"set mode safe", "set mode auto"}


def resolve_at_mentions(user_input: str, workspace_root: Optional[str] = None) -> str:
    """
    Expand @filename references in user input.
    e.g. "fix the bug in @main.py" → appends the file contents to the message.
    """
    pattern = re.compile(r"@([\w./\\-]+)")
    matches = pattern.findall(user_input)
    if not matches:
        return user_input

    injections = []
    for filename in matches:
        search_paths = [Path(filename)]
        if workspace_root:
            search_paths.insert(0, Path(workspace_root) / filename)

        for path in search_paths:
            try:
                content = path.read_text(encoding="utf-8")
                lines = content.splitlines()
                injections.append(
                    f"\n\n--- Contents of {filename} ({len(lines)} lines) ---\n{content}\n---"
                )
                console.print(
                    f"  [dim]@{filename} → injected {len(lines)} lines[/dim]"
                )
                break
            except FileNotFoundError:
                continue
            except Exception as exc:
                console.print(f"  [bold red]@{filename}: could not read — {exc}[/bold red]")
                break
        else:
            console.print(f"  [bold yellow]@{filename}: file not found, skipping[/bold yellow]")

    return user_input + "".join(injections)


def display_tool_log(tool_name: str, message: str) -> None:
    """Display a simple tool log line (legacy / internal use)."""
    console.print(f"  [bold cyan][TOOL][/bold cyan] [yellow]{tool_name}[/yellow] — {message}")


def display_tool_call(tool_name: str, arguments: dict, result: dict) -> None:
    """
    Display a tool call visibly in the terminal so it's clear what the agent is doing.
    Shows the tool name, arguments, status, and a brief output preview.
    """
    args_str = json.dumps(arguments)
    if len(args_str) > 80:
        args_str = args_str[:77] + "..."

    status = result.get("status", "unknown")
    if status == "success":
        status_markup = "[bold green]✓[/bold green]"
    else:
        status_markup = "[bold red]✗[/bold red]"

    # Build output preview: line count + first non-empty line
    output = result.get("output") or result.get("message") or ""
    output_str = str(output)
    lines = [l for l in output_str.splitlines() if l.strip()]
    if lines:
        line_count = len(output_str.splitlines())
        preview = lines[0][:80] + ("…" if len(lines[0]) > 80 else "")
        output_hint = f"  [dim]   └ {line_count} lines · {preview}[/dim]"
    else:
        output_hint = None

    console.print(
        f"  [bold cyan]⚙ Tool:[/bold cyan] [yellow]{tool_name}[/yellow]  "
        f"[dim]{args_str}[/dim]  {status_markup}"
    )
    if output_hint:
        console.print(output_hint)


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


def _load_prefs() -> dict:
    try:
        if _PREFS_FILE.exists():
            return json.loads(_PREFS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_prefs(prefs: dict) -> None:
    try:
        _PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PREFS_FILE.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
    except Exception:
        pass


def ask_execution_mode() -> bool:
    """
    Ask the user to choose safe or auto mode at startup.
    Saves the choice so subsequent runs skip the prompt.
    Returns True for safe mode, False for auto mode.
    """
    prefs = _load_prefs()

    if "execution_mode" in prefs:
        saved = prefs["execution_mode"]
        safe_mode = saved == "safe"
        mode_label = "[bold red]SAFE[/bold red]" if safe_mode else "[bold green]AUTO[/bold green]"
        console.print(
            f"\n  Mode: {mode_label}  "
            "[dim](saved — type [bold]set mode safe[/bold] or [bold]set mode auto[/bold] to change)[/dim]\n"
        )
        return safe_mode

    # First run — ask the user
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

    prefs["execution_mode"] = choice
    _save_prefs(prefs)
    return safe_mode


def display_help(safe_mode: bool = False, registry: Optional[Any] = None) -> None:
    """Display available commands and loaded tools."""
    mode_label = "[bold red]SAFE[/bold red]" if safe_mode else "[bold green]AUTO[/bold green]"
    lines = [
        f"[bold]Vertex — AI Coding Assistant[/bold]  (mode: {mode_label})\n",
        "[bold cyan]Commands:[/bold cyan]",
        "  [bold]set mode safe[/bold]   — confirm before each write/shell tool",
        "  [bold]set mode auto[/bold]   — execute all tools automatically",
        "  [bold]/help[/bold]           — show this help",
        "  [bold]exit / quit / q[/bold] — quit\n",
        "[bold cyan]Tips:[/bold cyan]",
        "  Use [bold]@filename[/bold] in your prompt to inject a file's contents automatically",
        "  e.g. [dim]fix the bug in @main.py[/dim]\n",
    ]
    if registry is not None:
        tool_names = registry.list_tools()
        lines.append(f"[bold cyan]Loaded tools ({len(tool_names)}):[/bold cyan]")
        lines.append("  [dim]" + "  ".join(tool_names) + "[/dim]")

    console.print(Panel("\n".join(lines), border_style="blue"))


def run_repl(
    agent_fn: Callable,
    executor: Optional[Any] = None,
    safe_mode: bool = False,
    registry: Optional[Any] = None,
    workspace_root: Optional[str] = None,
) -> None:
    """
    Run the main REPL loop.

    Args:
        agent_fn:      Callable(user_input, on_stream_chunk=None, on_usage=None) -> str.
        executor:      ToolExecutor — allows live mode switching.
        safe_mode:     Initial execution mode.
        registry:      ToolRegistry — used by /help to list loaded tools.
        workspace_root: Base path for resolving @file mentions.
    """
    display_welcome(safe_mode=safe_mode)

    current_safe_mode = safe_mode

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

        # /help command
        if user_input.lower() == "/help":
            display_help(safe_mode=current_safe_mode, registry=registry)
            continue

        # Live mode switching
        cmd = user_input.lower()
        if cmd == "set mode safe":
            current_safe_mode = True
            if executor:
                executor.set_safe_mode(True)
            prefs = _load_prefs()
            prefs["execution_mode"] = "safe"
            _save_prefs(prefs)
            console.print(
                "  [bold red]SAFE MODE[/bold red] enabled. "
                "[dim]Agent will ask for confirmation before write/shell commands.[/dim]"
            )
            continue
        if cmd == "set mode auto":
            current_safe_mode = False
            if executor:
                executor.set_safe_mode(False)
            prefs = _load_prefs()
            prefs["execution_mode"] = "auto"
            _save_prefs(prefs)
            console.print(
                "  [bold green]AUTO MODE[/bold green] enabled. "
                "[dim]Agent will execute all tools automatically.[/dim]"
            )
            continue

        # Resolve @file mentions before sending to agent
        user_input = resolve_at_mentions(user_input, workspace_root=workspace_root)

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
