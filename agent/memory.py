"""
Memory — Person 5
Person 1 calls add_user_message(), add_assistant_message(), get_history().
"""
from typing import Any, List

DEFAULT_MAX_MESSAGES = 20


class Memory:
    """
    Store conversation history with sliding window.

    API (Person 1 uses these):
        memory.add_user_message(content)
        memory.add_assistant_message(content)
        memory.get_history() -> List[dict]
    """

    def __init__(self, max_messages: int = DEFAULT_MAX_MESSAGES) -> None:
        self.history: List[dict] = []
        self.max_messages = max_messages

    def add_user_message(self, content: Any) -> None:
        """Add user message. Trim if over max."""
        self._add("user", content)

    def add_assistant_message(self, content: Any) -> None:
        """Add assistant message. Trim if over max."""
        self._add("assistant", content)

    def get_history(self) -> List[dict]:
        """Return conversation history."""
        return self.history

    def _add(self, role: str, content: Any) -> None:
        """Internal: add message and trim if over max."""
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_messages:
            self.history = self.history[-self.max_messages :]

    # Legacy aliases (prefer add_user_message/add_assistant_message in agent loop)
    def add(self, role: str, content: Any) -> None:
        """Legacy: prefer add_user_message/add_assistant_message."""
        self._add(role, content)

    def get(self) -> List[dict]:
        """Legacy: prefer get_history()."""
        return self.get_history()
