"""
OpenAI Provider — Person 3
"""
from typing import Any, Dict, List


class OpenAIProvider:
    """OpenAI API provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model

    def generate(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        # TODO: Call OpenAI API with function calling
        # TODO: Normalize response to {"content": "...", "tool_call": {...}}
        pass
