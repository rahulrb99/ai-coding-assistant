"""
AI Coding Assistant CLI — Main entry point.
Person 1: Wire everything together.
"""
import logging
import sys
import json
import re
import os
from pathlib import Path
from typing import Optional

# Add project root to path so all modules resolve correctly
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import get_settings
from agent.agent_loop import run_agent_loop, SYSTEM_PROMPT
from agent.memory import Memory
from agent.prompt_builder import build
from cli.interface import (
    run_repl,
    display_error,
    display_tool_call,
    ask_execution_mode,
    ask_model_provider,
)
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


def _available_providers_from_env() -> list[str]:
    """Return providers available based on installed/runtime capabilities."""
    providers: list[str] = []
    if os.getenv("GROQ_API_KEY", "").strip():
        providers.append("groq")
    if os.getenv("OPENAI_API_KEY", "").strip():
        providers.append("openai")
    # Ollama has no API key; expose as option always
    providers.append("ollama")
    # stable unique order
    out: list[str] = []
    for p in providers:
        if p not in out:
            out.append(p)
    return out


def _settings_for_provider(base_settings: dict, provider_name: str) -> dict:
    """Build runtime settings for the chosen provider without mutating .env."""
    s = dict(base_settings)
    s["model_provider"] = provider_name
    if provider_name == "groq":
        s["api_key"] = os.getenv("GROQ_API_KEY", "").strip() or None
        if not s.get("model_name") or ":" in str(s["model_name"]):
            s["model_name"] = "llama-3.3-70b-versatile"
    elif provider_name == "openai":
        s["api_key"] = os.getenv("OPENAI_API_KEY", "").strip() or None
        if not s.get("model_name") or "llama" in str(s["model_name"]).lower():
            s["model_name"] = "gpt-4o-mini"
    elif provider_name == "ollama":
        s["api_key"] = None
        if not s.get("model_name") or "llama-" in str(s["model_name"]).lower():
            s["model_name"] = "llama3.2:3b"
    return s


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
                status = "[bold green]connected[/bold green]"
            else:
                status = "[dim]unavailable[/dim]"
            table.add_row(server, str(count), status)

        if not mcp.server_stats:
            table.add_row("[dim]none[/dim]", "0", "[dim]no servers configured[/dim]")

        _con.print(table)
        if total:
            _con.print(f"  [dim]{total} MCP tool(s) ready[/dim]")
    except Exception as exc:
        logging.getLogger("MCP").warning("MCP tool loading failed (continuing with local tools): %s", exc)


def _extract_json_object(text: str) -> Optional[dict]:
    """Best-effort parse of first JSON object found in model output."""
    if not text:
        return None
    text = text.strip()
    # Fast path: whole text is JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # Fallback: locate first {...} block
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def _classify_needs_plan(provider: object, user_input: str) -> bool:
    """
    LLM-only classification (user-selected strategy 1A):
    require plan only for repo-changing multi-step tasks.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You classify developer requests.\n"
                "Return ONLY JSON with keys:\n"
                "  requires_repo_changes: boolean\n"
                "  is_multi_step: boolean\n"
                "Decide TRUE for requires_repo_changes only if task needs write_file/edit_file/run_shell.\n"
                "Decide TRUE for is_multi_step only if task needs multiple distinct steps, not a single action.\n"
            ),
        },
        {"role": "user", "content": user_input},
    ]
    response = provider.generate(messages, tools=[])
    content = (response or {}).get("content") or ""
    data = _extract_json_object(content) or {}
    return bool(data.get("requires_repo_changes")) and bool(data.get("is_multi_step"))


def _maybe_repo_change_hint(user_input: str) -> bool:
    """Cheap prefilter to avoid extra LLM call when clearly not a repo-changing request."""
    text = user_input.lower()
    keywords = (
        "create ", "write ", "edit ", "modify ", "update ",
        "refactor", "fix ", "add ", "remove ",
        "run ", "install ", "pip ", "npm ", "pytest", "test ",
        ".py", ".md", "file", "folder", "directory",
    )
    return any(k in text for k in keywords)


def _generate_plan(provider: object, user_input: str, feedback: Optional[str] = None) -> str:
    """Generate a concise execution plan for the task."""
    prompt = (
        "Create a concrete implementation plan before making changes.\n"
        "Rules:\n"
        "- 4 to 8 numbered steps.\n"
        "- Focus on files to inspect/change and validation steps.\n"
        "- Keep concise and actionable.\n"
        "- Do not execute anything; plan only.\n"
    )
    if feedback:
        prompt += f"\nUser feedback on previous plan:\n{feedback}\n"
    prompt += f"\nTask:\n{user_input}"
    response = provider.generate(
        [
            {"role": "system", "content": "You are a planning assistant. Return only the plan text."},
            {"role": "user", "content": prompt},
        ],
        tools=[],
    )
    return ((response or {}).get("content") or "").strip()


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
    available_providers = _available_providers_from_env()
    chosen_provider = ask_model_provider(available_providers, settings["model_provider"])

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
    provider_settings = _settings_for_provider(settings, chosen_provider)
    provider = _build_provider(provider_settings)
    memory = Memory()

    if memory.history:
        from rich.console import Console
        # Avoid unicode glyphs that can crash on legacy Windows consoles (cp1252).
        Console().print(
            f"  [dim]<- Restored {len(memory.history)} messages from previous session.[/dim]"
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

    def planner_fn(user_input: str, feedback: Optional[str] = None) -> dict:
        """
        Auto plan mode:
        - classify with LLM (1A)
        - if repo-changing + multi-step, generate plan
        """
        if not _maybe_repo_change_hint(user_input):
            return {"requires_plan": False, "plan": ""}
        needs_plan = _classify_needs_plan(provider, user_input)
        if not needs_plan:
            return {"requires_plan": False, "plan": ""}
        plan = _generate_plan(provider, user_input, feedback=feedback)
        return {"requires_plan": True, "plan": plan}

    def switch_provider(provider_name: str) -> tuple[bool, str]:
        nonlocal provider, provider_settings
        try:
            provider_settings = _settings_for_provider(settings, provider_name)
            provider = _build_provider(provider_settings)
            return True, f"model={provider_settings['model_name']}"
        except Exception as exc:
            return False, str(exc)

    run_repl(
        agent_fn,
        planner_fn=planner_fn,
        provider_switcher=switch_provider,
        available_providers=available_providers,
        executor=executor,
        safe_mode=safe_mode,
        registry=registry,
        workspace_root=workspace_root,
        memory=memory,
    )


class _PromptBuilderAdapter:
    """
    Thin adapter so agent_loop can call prompt_builder.build(...).
    Delegates to the module-level build() function from agent/prompt_builder.py.
    """

    def build(self, system_prompt: str, tools: list, history: list, user_input: str) -> list:
        return build(system_prompt=system_prompt, tools=tools, history=history, user_input=user_input)


if __name__ == "__main__":
    main()
