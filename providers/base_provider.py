"""Base provider interface for normalized LLM responses."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional


NormalizedResponse = Dict[str, Any]


class LLMProvider(ABC):
    """Base class for LLM providers. Enforces a shared response contract."""

    @abstractmethod
    def generate(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> NormalizedResponse:
        """Generate a single response. Must return normalized dict."""

    def stream_response(self, messages: List[Dict[str, Any]]) -> Iterator[str]:
        """
        Stream the final text response as chunks (no tool calling).
        Default implementation calls generate() and yields the full content at once.
        Providers can override this for true token-by-token streaming.
        """
        result = self.generate(messages, tools=[])
        content = result.get("content") or ""
        if content:
            yield content

    def _normalize(
        self,
        content: Optional[str],
        tool_call: Optional[Dict[str, Any]],
        usage: Optional[Dict[str, int]] = None,
    ) -> NormalizedResponse:
        """Create the shared response envelope for the agent loop."""
        return {
            "content": content,
            "tool_call": tool_call,
            "usage": usage,  # {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
        }
