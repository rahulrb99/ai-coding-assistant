"""OpenAI Provider — Person 3
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

from providers.base_provider import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API provider using function calling."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.model = model
        self.client = OpenAI(api_key=api_key)

    def generate(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Call OpenAI chat completion and normalize response.
        """
        functions = _build_openai_functions(tools)

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if functions:
            kwargs["functions"] = functions
            kwargs["function_call"] = "auto"

        completion = self.client.chat.completions.create(**kwargs)
        choice = completion.choices[0]
        message = _get_message(choice)

        content = _get_field(message, "content")
        function_call = _get_field(message, "function_call")

        parsed_tool_call: Optional[Dict[str, Any]] = None
        if function_call:
            name = _get_field(function_call, "name") or ""
            arguments = _parse_arguments(_get_field(function_call, "arguments"))
            tool_id = _get_field(function_call, "id") or f"openai_{name}"
            parsed_tool_call = {"id": tool_id, "name": name, "arguments": arguments}

        usage: Optional[Dict[str, int]] = None
        if completion.usage:
            usage = {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens,
            }

        return self._normalize(content, parsed_tool_call, usage)


def _build_openai_functions(tool_schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert internal tool schema format to OpenAI function calling format."""
    functions: List[Dict[str, Any]] = []
    for schema in tool_schemas:
        functions.append(
            {
                "name": schema.get("name", ""),
                "description": schema.get("description", ""),
                "parameters": schema.get("schema", {"type": "object", "properties": {}}),
            }
        )
    return functions


def _get_message(choice: Any) -> Dict[str, Any]:
    """Ensure we always work with a mutable mapping for the response message."""
    message = getattr(choice, "message", None)
    if message is None:
        try:
            message = choice["message"]
        except Exception:
            message = {}
    return message


def _get_field(message: Any, field: str) -> Optional[Any]:
    """Helper to read attribute or key from OpenAI objects."""
    if message is None:
        return None
    value = getattr(message, field, None)
    if value is not None:
        return value
    if isinstance(message, dict):
        return message.get(field)
    return None


def _parse_arguments(raw: Any) -> Dict[str, Any]:
    """Parse arguments into a dict, handling both dict and JSON string cases."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Failed to decode function_call arguments: %s", raw)
    return {}
