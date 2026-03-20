"""
Tool Executor — Person 2
Person 1 calls executor.execute(tool_name, arguments).
Validate, confirm (SAFE_MODE), execute, format result.
"""
from pathlib import Path
from tools.registry import ToolRegistry

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

            # Step 4: if safe_mode and tool_name in WRITE_TOOLS — ask input() confirm
            if self.safe_mode and tool_name in WRITE_TOOLS:
                answer = input(f"Confirm running {tool_name}? (y/N): ").strip().lower()
                if answer not in {"y", "yes"}:
                    return self._error(tool_name, "Cancelled by user.")

            # Step 5: call tool.execute(**params) and return result
            return tool.execute(**params)

        except Exception as e:
            # Step 6: catch any Exception and return error dict
            return self._error(tool_name, str(e))

    def set_safe_mode(self, enabled: bool) -> None:
        self.safe_mode = enabled
