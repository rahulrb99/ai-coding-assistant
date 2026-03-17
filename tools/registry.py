"""
Tool Registry — Person 2
Central store for local and MCP tools.
"""
from typing import Any, Dict, List, Optional


class ToolRegistry:
    """Register and lookup tools. Expose schemas for LLM."""

    def __init__(self) -> None:
        self._tools: Dict[str, Any] = {}

    def register(self, tool: Any) -> None:
        """Register a tool by name."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Any]:
        """Get tool by name."""
        return self._tools.get(name)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return JSON schemas for all tools (for LLM)."""
        return [tool.schema for tool in self._tools.values()]
