"""
Agent Loop — Person 1
ReAct pattern. MAX_ITERATIONS = 10.
Delegates tool execution to Tool Executor (never executes tools directly).
"""
from typing import Any, Optional

MAX_ITERATIONS = 10


def run_agent_loop(
    user_input: str,
    provider: Any,
    executor: Any,
    memory: Any,
    prompt_builder: Any,
    tool_registry: Any,
    system_prompt: str,
) -> str:
    """
    Run the ReAct agent loop until task complete or max iterations.
    Returns final response or error message.

    Pseudocode:
        memory.add_user_message(user_input)
        for i in range(MAX_ITERATIONS):
            messages = prompt_builder.build(system_prompt, tools, memory.get_history(), user_input)
            response = provider.generate(messages, tools)
            if response.get("tool_call"):
                tc = response["tool_call"]
                result = executor.execute(tc["name"], tc["arguments"])
                memory.add_assistant_message(response.get("content") or f"Tool: {tc['name']}")
                memory.add_user_message(str(result))
            else:
                return response.get("content") or ""
        return "Task could not be completed within allowed steps"
    """
    # TODO: Implement per pseudocode above
    pass
