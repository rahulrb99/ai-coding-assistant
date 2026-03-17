"""
Mocks for parallel development — Person 1
Use these to implement the Agent Loop before real Provider, Executor, Memory exist.
See CONTRACTS.md for interface specs.
"""
from typing import Any, Dict, List, Optional


class MockProvider:
    """Contract 3 mock. Returns configurable response."""

    def __init__(self, content: str = "hello", tool_call: Optional[Dict[str, Any]] = None) -> None:
        self.content = content
        self.tool_call = tool_call

    def generate(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return {"content": self.content, "tool_call": self.tool_call}


class MockExecutor:
    """Contract 2 mock. Returns success for any tool."""

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "success", "tool": tool_name, "output": "ok"}


class MockMemory:
    """Contract 5 mock."""

    def __init__(self) -> None:
        self.history: List[dict] = []

    def add_user_message(self, content: Any) -> None:
        self.history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: Any) -> None:
        self.history.append({"role": "assistant", "content": content})

    def get_history(self) -> List[dict]:
        return self.history
