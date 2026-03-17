"""
Base LLM Provider — Person 3
All providers return normalized output. One tool call per iteration.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class LLMProvider(ABC):
    """
    Base class for LLM providers. All providers must implement generate.

    API: provider.generate(messages, tools) -> dict
    Return format (normalized):
        {
            "content": str | None,
            "tool_call": {"name": str, "arguments": dict} | None
        }
    Only one tool_call per iteration. If tool_call present, content may be None.
    """

    @abstractmethod
    def generate(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate response. Return normalized format.
        content: str | None
        tool_call: {"name": str, "arguments": dict} | None  (at most one per call)
        """
        pass
