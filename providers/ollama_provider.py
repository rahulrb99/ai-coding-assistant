"""Ollama Provider — Person 3
Calls a local Ollama instance. No API key required.
Ollama must be running: https://ollama.com/download
Default base URL: http://localhost:11434
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterator, List, Optional

from providers.base_provider import LLMProvider

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaProvider(LLMProvider):
    """
    Ollama local LLM provider.

    Requirements:
        pip install ollama
        ollama pull <model>   # e.g. ollama pull llama3.2
        ollama serve          # starts the local server
    """

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = _DEFAULT_BASE_URL,
    ) -> None:
        self.model = model
        self.base_url = base_url
        try:
            import ollama as _ollama_lib
            self._client = _ollama_lib.Client(host=base_url)
        except ImportError as exc:
            raise ImportError(
                "ollama package not installed. Run: pip install ollama"
            ) from exc

    def generate(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Call Ollama chat API and normalize response.
        Tool calling uses Ollama's native function calling (supported on llama3.1+).
        """
        ollama_tools = _build_ollama_tools(tools) if tools else None

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if ollama_tools:
            kwargs["tools"] = ollama_tools

        try:
            response = self._client.chat(**kwargs)
        except Exception as exc:
            logger.error("Ollama API error: %s", exc)
            raise

        message = response.message

        content: Optional[str] = message.content or None
        tool_call: Optional[Dict[str, Any]] = None

        if hasattr(message, "tool_calls") and message.tool_calls:
            tc = message.tool_calls[0]
            try:
                func = tc.function
                name = func.name
                arguments = func.arguments if isinstance(func.arguments, dict) else json.loads(func.arguments or "{}")
            except (AttributeError, json.JSONDecodeError):
                name, arguments = "", {}
            tool_call = {
                "id": f"ollama_{name}",
                "name": name,
                "arguments": arguments,
            }

        # Ollama doesn't expose token usage in the same way; set to None
        usage: Optional[Dict[str, int]] = None
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }

        return self._normalize(content, tool_call, usage)

    def stream_response(self, messages: List[Dict[str, Any]]) -> Iterator[str]:
        """Stream final response token-by-token from Ollama."""
        stream = self._client.chat(
            model=self.model,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.message.content
            if delta:
                yield delta


def _build_ollama_tools(tool_schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert internal tool schema format to Ollama's function calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "parameters": t.get("schema", {"type": "object", "properties": {}}),
            },
        }
        for t in tool_schemas
    ]
