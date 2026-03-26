"""
Tool Executor — Person 2
Person 1 calls executor.execute(tool_name, arguments).
Validate, confirm (SAFE_MODE), execute, format result.
"""
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from tools.registry import ToolRegistry

_console = Console()

WRITE_TOOLS = {"write_file", "edit_file", "run_shell"}


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, workspace_root: str = "./workspace", safe_mode: bool = True):
        self.registry = registry
        self.workspace_root = Path(workspace_root).resolve()
        self.safe_mode = safe_mode

    def _error(self, tool_name: str, message: str) -> dict:
        return {"status": "error", "tool": tool_name, "message": message}

    def execute(self, tool_name: str, params: dict) -> dict:
        try:
            # Step 1: look up tool — error if not found
            tool = self.registry.get_tool(tool_name)
            if tool is None:
                return self._error(tool_name, f"Unknown tool: {tool_name}")

            # Step 2: check required params from tool.schema.get("required", [])
            schema = getattr(tool, "schema", {}) or {}
            required = []
            if isinstance(schema, dict):
                required = schema.get("required", []) or []
            missing = [k for k in required if k not in params]
            if missing:
                return self._error(tool_name, f"Missing required parameter(s): {', '.join(missing)}")

            # Step 3: if "path" in params, validate it stays inside workspace_root
            if "path" in params and isinstance(params["path"], str):
                rel = Path(params["path"])
                if rel.is_absolute():
                    return self._error(tool_name, "Security error: path must be relative to workspace_root.")
                target = (self.workspace_root / rel).resolve()
                try:
                    target.relative_to(self.workspace_root)
                except ValueError:
                    return self._error(tool_name, "Security error: path escapes workspace_root.")

            # Step 4: if safe_mode and tool_name in WRITE_TOOLS — ask for confirmation
            if self.safe_mode and tool_name in WRITE_TOOLS:
                _console.print(
                    f"\n  [bold yellow]⚠  Safe Mode:[/bold yellow] Agent wants to run "
                    f"[bold cyan]{tool_name}[/bold cyan]"
                )
                confirmed = Confirm.ask("  Allow this action?", default=False)
                if not confirmed:
                    _console.print("  [dim]Action cancelled.[/dim]")
                    return self._error(tool_name, "Cancelled by user.")

            # Step 5: call tool.execute(**params) and return result
            return tool.execute(**params)

        except Exception as e:
            # Step 6: catch any Exception and return error dict
            return self._error(tool_name, str(e))

    def set_safe_mode(self, enabled: bool) -> None:
        self.safe_mode = enabled
