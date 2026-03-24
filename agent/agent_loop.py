"""
Agent Loop — Person 1
ReAct pattern. MAX_ITERATIONS = 10.
Delegates tool execution to Tool Executor (never executes tools directly).
"""
import json
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger("AGENT")

MAX_ITERATIONS = 10

SYSTEM_PROMPT = (
    "You are an AI coding assistant. "
    "Use the available tools to help the user with coding tasks. "
    "Read files before editing them. After editing, read the file again to verify changes. "
    "Think step by step. When the task is done, respond with a clear final answer."
)


def run_agent_loop(
    user_input: str,
    provider: Any,
    executor: Any,
    memory: Any,
    prompt_builder: Any,
    tool_registry: Any,
    system_prompt: str = SYSTEM_PROMPT,
    on_tool_call: Optional[Callable[[str, dict, dict], None]] = None,
) -> str:
    """
    Run the ReAct agent loop until task complete or max iterations.
    Returns final response or error message.
    """
    tools = tool_registry.get_tool_schemas()

    memory.add_user_message(user_input)
    logger.info("Starting agent loop. user_input=%r", user_input[:120])

    for iteration in range(MAX_ITERATIONS):
        logger.info("Iteration %d/%d", iteration + 1, MAX_ITERATIONS)

        messages = prompt_builder.build(
            system_prompt=system_prompt,
            tools=tools,
            history=memory.get_history(),
            user_input=user_input,
        )

        try:
            response = provider.generate(messages, tools)
        except Exception as exc:
            logger.error("LLM provider error: %s", exc)
            return f"Error: LLM provider failed — {exc}"

        if not response or not isinstance(response, dict):
            logger.error("Provider returned invalid response: %r", response)
            return "Error: LLM provider returned an invalid response. The provider may not be implemented yet."

        tool_call = response.get("tool_call")
        content = response.get("content") or ""

        if tool_call:
            tool_name = tool_call.get("name", "")
            tool_call_id = tool_call.get("id", f"call_{tool_name}")
            arguments = tool_call.get("arguments") or {}

            logger.info("[TOOL] %s args=%r", tool_name, arguments)

            result = executor.execute(tool_name, arguments)
            tool_output = result.get("output") or result.get("message") or str(result)

            if on_tool_call:
                on_tool_call(tool_name, arguments, result)

            # Store assistant's tool-call decision in the format Groq expects
            memory.add_raw_message({
                "role": "assistant",
                "content": content or "",
                "tool_calls": [{
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(arguments),
                    },
                }],
            })

            # Store tool result with role="tool" and matching tool_call_id
            memory.add_raw_message({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": tool_output,
            })

            logger.info("[TOOL] result status=%s", result.get("status"))
        else:
            # No tool call — the LLM has produced a final answer
            memory.add_assistant_message(content)
            logger.info("Final answer returned after %d iteration(s)", iteration + 1)
            return content

    logger.warning("MAX_ITERATIONS (%d) reached without final answer", MAX_ITERATIONS)
    return "Task could not be completed within the allowed number of steps. Please try again or break the task into smaller parts."
