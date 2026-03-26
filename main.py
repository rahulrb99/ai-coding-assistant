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
    # Avoid adding duplicate handlers if logging was already configured
    if root.handlers:
        return

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
            return OllamaProvider(model=settings["model_name"])
        except ImportError:
            logging.getLogger("AGENT").warning(
                "OllamaProvider not yet implemented. Using MockProvider."
            )

    # Fallback mock when provider is not ready or key not set
    from agent.mocks import MockProvider
    logging.getLogger("AGENT").warning(
        "No valid API key found for provider '%s'. Using MockProvider.", provider_name
    )
    return MockProvider(content="[MockProvider] Provider not configured. Please set API keys in .env.")


def _load_mcp_tools(registry: ToolRegistry, settings: dict) -> None:
    """Connect to MCP servers and load their tools into the registry. Non-fatal on failure."""
    try:
        from rich.console import Console
        Console().print("  [dim]Connecting to MCP servers...[/dim]")
        mcp = MCPClient(registry=registry)
        mcp.connect_and_load()
        tool_names = registry.list_tools()
        mcp_tools = [t for t in tool_names if t not in {
            "read_file", "write_file", "edit_file", "run_shell", "search_codebase"
        }]
        if mcp_tools:
            from rich.console import Console
            Console().print(
                f"  [bold green]MCP:[/bold green] {len(mcp_tools)} server tool(s) loaded: "
                f"[dim]{', '.join(mcp_tools)}[/dim]"
            )
        else:
            from rich.console import Console
            Console().print("  [dim]MCP: No server tools loaded (servers may be unavailable).[/dim]")
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

    # Wrap the agent loop into a single callable for the REPL
    def agent_fn(user_input: str, on_stream_chunk=None, on_usage=None) -> str:
        return run_agent_loop(
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

    run_repl(agent_fn, executor=executor, safe_mode=safe_mode)


class _PromptBuilderAdapter:
    """
    Thin adapter so agent_loop can call prompt_builder.build(...).
    Delegates to the module-level build() function from agent/prompt_builder.py.
    """

    def build(self, system_prompt: str, tools: list, history: list, user_input: str) -> list:
        return build(system_prompt=system_prompt, tools=tools, history=history, user_input=user_input)


if __name__ == "__main__":
    main()
