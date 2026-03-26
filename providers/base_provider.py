"""Base provider interface for normalized LLM responses."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


NormalizedResponse = Dict[str, Any]


class LLMProvider(ABC):
    """Base class for LLM providers. Enforces a shared response contract."""

    @abstractmethod
    def generate(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> NormalizedResponse:
        """Generate a single response. Must return normalized dict."""

    def _normalize(
        self, content: Optional[str], tool_call: Optional[Dict[str, Any]]
    ) -> NormalizedResponse:
        """Create the shared response envelope for the agent loop."""
        return {
            "content": content,
            "tool_call": tool_call,
        }
