"""
Tool interface — Person 2
All tools must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class Tool(ABC):
    """
    Base class for all tools (local and MCP-wrapped).

    Interface: name, description, schema, execute(**kwargs) -> dict
    Return format (frozen):
        Success: {"status": "success", "tool": "<name>", "output": "..."}
        Error:   {"status": "error", "tool": "<name>", "message": "..."}
    """

    name: str = ""
    description: str = ""
    schema: Dict[str, Any] = {}

    @abstractmethod
    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute the tool. Return structured result.
        Success: {"status": "success", "tool": self.name, "output": "..."}
        Error:   {"status": "error", "tool": self.name, "message": "..."}
        """
        pass
