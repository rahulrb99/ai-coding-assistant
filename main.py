"""
AI Coding Assistant CLI — Main entry point.
Person 1: Wire everything together.
"""
import logging
import sys
from pathlib import Path

# Add project root to path so all modules resolve correctly
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import get_settings
from agent.agent_loop import run_agent_loop, SYSTEM_PROMPT
from agent.memory import Memory
from agent.prompt_builder import build
from cli.interface import run_repl, display_error, display_tool_call, ask_execution_mode
from tools.registry import ToolRegistry
from tools.executor import ToolExecutor
from tools.read_file import ReadFileTool
from tools.write_file import WriteFileTool
from tools.edit_file import EditFileTool
from tools.run_shell import RunShellTool
from tools.search_codebase import SearchCodebaseTool
from mcp.mcp_client import MCPClient


def _setup_logging() -> None:
    """Configure logging to .logs/agent.log (and console for WARNING+)."""
    log_dir = Path(".logs")
    log_dir.mkdir(exist_ok=True)

    root = logging.getLogger()

    # Only add handlers once — but ALWAYS apply the suppression below
    if not root.handlers:
        root.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s [%(name)s] %(message)s")

        file_handler = logging.FileHandler(log_dir / "agent.log", encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(fmt)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(fmt)

        root.addHandler(file_handler)
        root.addHandler(console_handler)

    # Always suppress third-party INFO noise from the terminal regardless of
    # whether handlers were already configured (some libs add handlers on import).
    for noisy in ("httpx", "httpcore", "mcp_client", "mcp.mcp_client", "mcp", "anyio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _build_provider(settings: dict):
    """Return the configured LLM provider, or a fallback mock if keys are missing."""
    provider_name = settings["model_provider"]
    api_key = settings.get("api_key")

    if provider_name == "openai" and api_key:
        from providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, model=settings["model_name"])

    if provider_name == "groq" and api_key:
        from providers.groq_provider import GroqProvider
        return GroqProvider(api_key=api_key, model=settings["model_name"])

    if provider_name == "ollama":
        try:
            from providers.ollama_provider import OllamaProvider
            import os
            base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            return OllamaProvider(model=settings["model_name"], base_url=base_url)
        except ImportError as exc:
            logging.getLogger("AGENT").warning("OllamaProvider unavailable: %s", exc)

    # Fallback mock when provider is not ready or key not set
    from agent.mocks import MockProvider
    logging.getLogger("AGENT").warning(
        "No valid API key found for provider '%s'. Using MockProvider.", provider_name
    )
    return MockProvider(content="[MockProvider] Provider not configured. Please set API keys in .env.")


def _load_mcp_tools(registry: ToolRegistry, settings: dict) -> None:
    """Connect to MCP servers and load their tools into the registry. Non-fatal on failure."""
    # Re-apply suppression here — mcp package can re-add handlers during async startup
    for noisy in ("httpx", "httpcore", "mcp_client", "mcp.mcp_client", "mcp", "anyio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    try:
        from rich.console import Console
        from rich.table import Table
        _con = Console()
        _con.print("  [dim]Connecting to MCP servers...[/dim]")
        mcp = MCPClient(registry=registry)
        mcp.connect_and_load()

        table = Table(title="MCP Servers", border_style="dim", show_lines=False)
        table.add_column("Server", style="cyan", no_wrap=True)
        table.add_column("Tools", justify="right")
        table.add_column("Status", justify="left")

        total = 0
        for server, count in mcp.server_stats.items():
            total += count
            if count > 0:
                status = "[bold green]✓ connected[/bold green]"
            else:
                status = "[dim]✗ unavailable[/dim]"
            table.add_row(server, str(count), status)

        if not mcp.server_stats:
            table.add_row("[dim]none[/dim]", "0", "[dim]no servers configured[/dim]")

        _con.print(table)
        if total:
            _con.print(f"  [dim]{total} MCP tool(s) ready[/dim]")
    except Exception as exc:
        logging.getLogger("MCP").warning("MCP tool loading failed (continuing with local tools): %s", exc)


def main() -> None:
    """Run the AI coding assistant."""
    _setup_logging()

    try:
        settings = get_settings()
    except ValueError as exc:
        display_error(str(exc))
        sys.exit(1)

    workspace_root = str(settings["workspace_root"])

    # Ask user to choose execution mode at startup (overrides .env default)
    safe_mode = ask_execution_mode()

    # Ensure workspace directory exists
    Path(workspace_root).mkdir(parents=True, exist_ok=True)

    # Build the tool registry with all local tools
    registry = ToolRegistry()
    registry.register(ReadFileTool(workspace_root=workspace_root))
    registry.register(WriteFileTool(workspace_root=workspace_root))
    registry.register(EditFileTool(workspace_root=workspace_root))
    registry.register(RunShellTool(workspace_root=workspace_root))
    registry.register(SearchCodebaseTool(workspace_root=workspace_root))

    # Load MCP tools on top of local tools (non-fatal if servers unavailable)
    _load_mcp_tools(registry, settings)

    executor = ToolExecutor(registry=registry, workspace_root=workspace_root, safe_mode=safe_mode)
    provider = _build_provider(settings)
    memory = Memory()

    if memory.history:
        from rich.console import Console
        Console().print(
            f"  [dim]↩ Restored {len(memory.history)} messages from previous session.[/dim]"
        )

    # Wrap the agent loop into a single callable for the REPL
    def agent_fn(user_input: str, on_stream_chunk=None, on_usage=None) -> str:
        result = run_agent_loop(
            user_input=user_input,
            provider=provider,
            executor=executor,
            memory=memory,
            prompt_builder=_PromptBuilderAdapter(),
            tool_registry=registry,
            system_prompt=SYSTEM_PROMPT,
            on_tool_call=display_tool_call,
            on_stream_chunk=on_stream_chunk,
            on_usage=on_usage,
        )
        memory.save()
        return result

    run_repl(agent_fn, executor=executor, safe_mode=safe_mode, registry=registry, workspace_root=workspace_root)


class _PromptBuilderAdapter:
    """
    Thin adapter so agent_loop can call prompt_builder.build(...).
    Delegates to the module-level build() function from agent/prompt_builder.py.
    """

    def build(self, system_prompt: str, tools: list, history: list, user_input: str) -> list:
        return build(system_prompt=system_prompt, tools=tools, history=history, user_input=user_input)


if __name__ == "__main__":
    main()
