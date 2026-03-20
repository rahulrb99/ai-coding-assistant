"""
Groq Provider — Person 3
Calls Groq API and normalizes response to the shared format.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from groq import Groq

logger = logging.getLogger(__name__)

# How many times to retry when Groq returns tool_use_failed
_MAX_TOOL_RETRIES = 2


class GroqProvider:
    """Groq API provider. Free tier available."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
        self.model = model
        self.client = Groq(api_key=api_key)

    def generate(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Call Groq API and normalize response.
        Returns: {"content": str | None, "tool_call": {"name": str, "arguments": dict} | None}

        Retries up to _MAX_TOOL_RETRIES times on tool_use_failed errors (model generated
        tool calls in the wrong XML format).  On the final retry, tools are dropped so the
        model falls back to a plain-text answer rather than crashing the loop.
        """
        groq_tools = _build_groq_tools(tools)

        last_exc: Optional[Exception] = None
        for attempt in range(_MAX_TOOL_RETRIES + 1):
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                # Disabling parallel tool calls greatly reduces malformed XML generations
                "parallel_tool_calls": False,
            }

            # On the last retry, drop tools entirely so we still get a useful text reply
            if groq_tools and attempt < _MAX_TOOL_RETRIES:
                kwargs["tools"] = groq_tools
                kwargs["tool_choice"] = "auto"

            try:
                completion = self.client.chat.completions.create(**kwargs)
            except Exception as exc:
                error_body = str(exc)
                if "tool_use_failed" in error_body:
                    logger.warning(
                        "tool_use_failed on attempt %d/%d — retrying%s",
                        attempt + 1,
                        _MAX_TOOL_RETRIES + 1,
                        " without tools" if attempt == _MAX_TOOL_RETRIES - 1 else "",
                    )
                    last_exc = exc
                    continue  # retry
                raise  # non-tool errors bubble up immediately

            choice = completion.choices[0]
            message = choice.message

            content: Optional[str] = message.content or None
            tool_call: Optional[Dict[str, Any]] = None

            if message.tool_calls:
                tc = message.tool_calls[0]
                try:
                    arguments = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                tool_call = {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": arguments,
                }

            return {"content": content, "tool_call": tool_call}

        # All retries exhausted — re-raise the last tool_use_failed error
        raise last_exc  # type: ignore[misc]


def _build_groq_tools(tool_schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert internal tool schema format to Groq's function-calling format."""
    groq_tools = []
    for t in tool_schemas:
        groq_tools.append({
            "type": "function",
            "function": {
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "parameters": t.get("schema", {"type": "object", "properties": {}}),
            },
        })
    return groq_tools
