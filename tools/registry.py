"""
Tool Registry — Person 2
Central store for local and MCP tools.
"""
from typing import Any, Dict, List, Optional


class ToolRegistry:
    """Register and lookup tools. Expose schemas for LLM."""

    def __init__(self) -> None:
        self._tools: Dict[str, Any] = {}

    def __len__(self) -> int:
        return len(self._tools)

    def register(self, tool: Any) -> None:
        """Register a tool by name."""
        name = getattr(tool, "name", "")
        if name == "":
            raise ValueError("Tool name cannot be empty.")
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        self._tools[name] = tool

    def get_tool(self, name: str) -> Optional[Any]:
        """Get tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return JSON schemas for all tools (for LLM)."""
        # Provide a stable schema envelope for callers/tests:
        # {"name": ..., "description": ..., "schema": {...}}
        schemas: List[Dict[str, Any]] = []
        for tool in self._tools.values():
            schemas.append(
                {
                    "name": getattr(tool, "name", ""),
                    "description": getattr(tool, "description", ""),
                    "schema": getattr(tool, "schema", {}),
                }
            )
        return schemas
