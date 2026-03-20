"""
Prompt Builder — Person 5
Person 1 calls build(system_prompt, tools, history, user_input).
Returns messages in OpenAI chat format.
"""
from typing import List

# Keep the last N messages when history grows too long.
# System message is always pinned and never truncated.
MAX_HISTORY_MESSAGES = 20


def build(
    system_prompt: str,
    tools: List[dict],
    history: List[dict],
    user_input: str,
) -> List[dict]:
    """
    Build the LLM prompt in the required order:
      1. System instructions (always pinned, never truncated)
      2. Conversation history (sliding window, oldest dropped first)

    Tools are passed separately to the provider via function calling
    and are NOT embedded as messages.

    Returns: List of {"role": str, "content": str} in OpenAI chat format.
    """
    # 1. System message — always first, never removed
    messages: List[dict] = [{"role": "system", "content": system_prompt}]

    # 2. Truncate history if it exceeds the sliding window
    truncated = history[-MAX_HISTORY_MESSAGES:] if len(history) > MAX_HISTORY_MESSAGES else history

    messages.extend(truncated)
    return messages


# Alias for backward compatibility
build_prompt = build
