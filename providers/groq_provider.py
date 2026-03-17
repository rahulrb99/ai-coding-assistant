"""
Groq Provider — Person 3
"""
from typing import Any, Dict, List


class GroqProvider:
    """Groq API provider. Free tier available."""

    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant") -> None:
        self.api_key = api_key
        self.model = model

    def generate(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        # TODO: Call Groq API with function calling
        # TODO: Normalize response to {"content": "...", "tool_call": {...}}
        pass
