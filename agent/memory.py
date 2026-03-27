"""
Memory — Person 5
Person 1 calls add_user_message(), add_assistant_message(), get_history().
"""
import json
import logging
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MAX_MESSAGES = 20
DEFAULT_HISTORY_FILE = Path(".logs/history.json")


class Memory:
    """
    Store conversation history with sliding window.
    Optionally persists to a JSON file so history survives restarts.

    API (Person 1 uses these):
        memory.add_user_message(content)
        memory.add_assistant_message(content)
        memory.get_history() -> List[dict]
    """

    def __init__(
        self,
        max_messages: int = DEFAULT_MAX_MESSAGES,
        persist_path: Optional[Path] = DEFAULT_HISTORY_FILE,
    ) -> None:
        self.history: List[dict] = []
        self.max_messages = max_messages
        self.persist_path = persist_path
        if persist_path:
            self._load()

    def add_user_message(self, content: Any) -> None:
        """Add user message. Trim if over max."""
        self._add("user", content)

    def add_assistant_message(self, content: Any) -> None:
        """Add assistant message. Trim if over max."""
        self._add("assistant", content)

    def get_history(self) -> List[dict]:
        """Return conversation history."""
        return self.history

    def add_raw_message(self, message: dict) -> None:
        """
        Append a fully-formed message dict (any role, e.g. 'tool').
        Used for function-calling tool results that require extra fields
        like tool_call_id which the simple add_*_message helpers don't support.
        """
        self.history.append(message)
        if len(self.history) > self.max_messages:
            self.history = self.history[-self.max_messages :]

    def _add(self, role: str, content: Any) -> None:
        """Internal: add message and trim if over max."""
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_messages:
            self.history = self.history[-self.max_messages :]

    def save(self) -> None:
        """Persist history to JSON file."""
        if not self.persist_path:
            return
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            self.persist_path.write_text(
                json.dumps(self.history, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:
            logger.warning("Failed to save history: %s", exc)

    def clear(self) -> None:
        """Clear in-memory history and persist the empty history (if enabled)."""
        self.history = []
        self.save()
    def _load(self) -> None:
        """Load history from JSON file if it exists."""
        if not self.persist_path or not self.persist_path.exists():
            return
        try:
            data = json.loads(self.persist_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self.history = data[-self.max_messages:]
                logger.info("Loaded %d messages from history file.", len(self.history))
        except Exception as exc:
            logger.warning("Failed to load history: %s", exc)

    # Legacy aliases (prefer add_user_message/add_assistant_message in agent loop)
    def add(self, role: str, content: Any) -> None:
        """Legacy: prefer add_user_message/add_assistant_message."""
        self._add(role, content)

    def get(self) -> List[dict]:
        """Legacy: prefer get_history()."""
        return self.get_history()
