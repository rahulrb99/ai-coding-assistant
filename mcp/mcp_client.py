"""
MCP Client — Person 4
Connect to MCP servers, discover tools, wrap and register in ToolRegistry.
"""
from typing import Any


def load_tools(registry: Any) -> None:
    """
    Connect to MCP servers (filesystem, Tavily/Context7, custom RAG).
    Discover tools, wrap as Tool objects, register in registry.
    """
    # TODO: Connect to filesystem server
    # TODO: Connect to Tavily or Context7
    # TODO: Connect to custom RAG server (Person 5)
    # TODO: For each server: discover tools, wrap, registry.register()
    pass


class MCPClient:
    """MCP client. Connects to servers and loads tools."""

    def __init__(self, registry: Any) -> None:
        self.registry = registry

    def connect_and_load(self) -> None:
        """Connect to all servers and load tools into registry."""
        load_tools(self.registry)
