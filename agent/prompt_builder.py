"""
Prompt Builder — Person 5
Person 1 calls build(system_prompt, tools, history, user_input).
Returns messages in OpenAI chat format.
"""
from typing import Any, List


def build(
    system_prompt: str,
    tools: List[dict],
    history: List[dict],
    user_input: str,
) -> List[dict]:
    """
    Build the LLM prompt. Person 1 calls this.

    Order: (1) System instructions, (2) Tool definitions, (3) History, (4) User request.
    Returns: messages (list of {"role": str, "content": str} in OpenAI chat format)
    """
    # TODO: Assemble in order: system, tools, history, user_input
    # TODO: Truncate history if needed (older first)
    # TODO: Reduce RAG chunks if still over limit
    # TODO: Return List[dict] e.g. [{"role":"system","content":"..."}, ...]
    pass


# Alias for backward compatibility
build_prompt = build
