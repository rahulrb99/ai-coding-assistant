"""
Agent Loop — Person 1
ReAct pattern. MAX_ITERATIONS = 10.
Delegates tool execution to Tool Executor (never executes tools directly).
"""
import json
import logging
import re
import time
from typing import Any, Callable, List, Optional

logger = logging.getLogger("AGENT")

MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # seconds; doubles each attempt (1 → 2 → 4)


def _extract_retry_after(exc: Exception) -> Optional[float]:
    """
    Parse a 'retry after Xs' hint from rate-limit error messages.
    Returns seconds to wait, or None if not found.
    """
    text = str(exc)
    match = re.search(r"try again in\s+([\d.]+)s", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    match = re.search(r"retry.after[:\s]+([\d.]+)", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _is_rate_limit(exc: Exception) -> bool:
    text = str(exc)
    return "429" in text or "rate_limit" in text.lower() or "rate limit" in text.lower()


def _generate_with_retry(
    provider: Any,
    messages: list,
    tools: list,
    on_retry: Optional[Callable[[int, float], None]] = None,
) -> dict:
    """
    Call provider.generate() with up to MAX_RETRIES retries and exponential backoff.
    on_retry(attempt, wait_secs) is called before each sleep so the UI can inform the user.
    Raises the last exception if all retries fail.
    """
    last_exc: Exception = RuntimeError("Unknown error")
    for attempt in range(MAX_RETRIES + 1):
        try:
            return provider.generate(messages, tools)
        except Exception as exc:
            last_exc = exc
            if attempt == MAX_RETRIES:
                break  # exhausted — re-raise below

            if _is_rate_limit(exc):
                wait = _extract_retry_after(exc) or (_RETRY_BASE_DELAY * (2 ** attempt))
                # Cap the wait at 120 s so we don't hang forever
                wait = min(wait, 120.0)
            else:
                wait = _RETRY_BASE_DELAY * (2 ** attempt)

            logger.warning(
                "LLM call failed (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, MAX_RETRIES, wait, exc,
            )
            if on_retry:
                on_retry(attempt + 1, wait)
            time.sleep(wait)

    raise last_exc

# Maximum tools to send to the LLM in a single call.
# Too many tools causes models to generate malformed tool calls.
MAX_TOOLS_PER_CALL = 12

# Tools that are always included regardless of the user query
_CORE_TOOLS = {
    "read_file", "write_file", "edit_file", "run_shell", "search_codebase",
    "tavily_search", "tavily_research", "list_directory", "directory_tree",
}


def _select_tools(all_tools: List[dict]) -> List[dict]:
    """
    Return a focused subset of tools so the LLM doesn't get overwhelmed.
    Core tools are always included; remaining slots filled by other tools.
    """
    if len(all_tools) <= MAX_TOOLS_PER_CALL:
        return all_tools

    core = [t for t in all_tools if t.get("name") in _CORE_TOOLS]
    others = [t for t in all_tools if t.get("name") not in _CORE_TOOLS]
    remaining_slots = MAX_TOOLS_PER_CALL - len(core)
    return core + others[:max(remaining_slots, 0)]

MAX_ITERATIONS = 10

SYSTEM_PROMPT = (
    "You are Vertex, an AI coding assistant. "
    "You have access to tools — always use them to complete tasks rather than guessing.\n\n"
    "Tool selection guide:\n"
    "- Use tavily_search or tavily_research for ANY question about current events, latest versions, "
    "recent documentation, or information you may not have in your training data.\n"
    "- Use read_file or read_text_file to read files on disk.\n"
    "- Use write_file to create or overwrite files.\n"
    "- Use edit_file to modify a specific section of an existing file.\n"
    "- Use run_shell to run commands, install packages, or execute scripts.\n"
    "- Use search_codebase or search_files to search for patterns in the local codebase.\n"
    "- Use list_directory or directory_tree to explore the file structure.\n\n"
    "Rules:\n"
    "- Read files before editing them.\n"
    "- After editing, read the file again to verify the change was applied.\n"
    "- Think step by step.\n"
    "- When the task is done, respond with a clear final answer.\n"
    "- When the user pastes an error message or traceback, ALWAYS start your response "
    "by briefly explaining: (1) what caused the error, and (2) what fix you are going "
    "to apply — BEFORE making any tool calls or writing any code.\n"
    "- IMPORTANT: Never run long-running server or watcher commands (e.g. streamlit run, "
    "flask run, npm start, uvicorn, pytest --watch) directly — they will time out and "
    "crash. Instead, write the file and tell the user to run the server themselves. "
    "If you must launch it, run it detached: on Windows use 'start /B <command>', "
    "on macOS/Linux use '<command> &' (e.g. 'streamlit run app.py &')."
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
    on_stream_chunk: Optional[Callable[[str], None]] = None,
    on_usage: Optional[Callable[[dict], None]] = None,
) -> str:
    """
    Run the ReAct agent loop until task complete or max iterations.
    Returns final response or error message.

    on_usage is called once at the end with aggregated token counts:
        {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
    """
    tools = _select_tools(tool_registry.get_tool_schemas())

    memory.add_user_message(user_input)
    logger.info("Starting agent loop. user_input=%r", user_input[:120])

    # Accumulate token usage across all LLM calls in this loop
    total_usage: dict = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _add_usage(usage: Optional[dict]) -> None:
        if not usage:
            return
        total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
        total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
        total_usage["total_tokens"] += usage.get("total_tokens", 0)

    for iteration in range(MAX_ITERATIONS):
        logger.info("Iteration %d/%d", iteration + 1, MAX_ITERATIONS)

        messages = prompt_builder.build(
            system_prompt=system_prompt,
            tools=tools,
            history=memory.get_history(),
            user_input=user_input,
        )

        try:
            response = _generate_with_retry(provider, messages, tools)
        except Exception as exc:
            logger.error("LLM provider error after %d retries: %s", MAX_RETRIES, exc)
            if _is_rate_limit(exc):
                retry_after = _extract_retry_after(exc)
                hint = f" — try again in {retry_after:.0f}s" if retry_after else ""
                return f"Error: Rate limit reached{hint}. Please wait and retry."
            return f"Error: LLM provider failed — {exc}"

        if not response or not isinstance(response, dict):
            logger.error("Provider returned invalid response: %r", response)
            return "Error: LLM provider returned an invalid response. The provider may not be implemented yet."

        _add_usage(response.get("usage"))

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
            # No tool call — stream the final answer if supported, else return full content
            logger.info("Final answer returned after %d iteration(s)", iteration + 1)
            if on_stream_chunk and hasattr(provider, "stream_response"):
                streamed_content = ""
                try:
                    for chunk in provider.stream_response(messages):
                        if isinstance(chunk, dict):
                            # Sentinel dict carrying usage stats from the stream
                            _add_usage(chunk.get("usage"))
                        else:
                            on_stream_chunk(chunk)
                            streamed_content += chunk
                    if on_usage and total_usage["total_tokens"]:
                        on_usage(total_usage)
                    memory.add_assistant_message(streamed_content)
                    return streamed_content
                except Exception as exc:
                    logger.warning("Streaming failed, falling back to non-streamed content: %s", exc)
            if on_usage and total_usage["total_tokens"]:
                on_usage(total_usage)
            memory.add_assistant_message(content)
            return content

    logger.warning("MAX_ITERATIONS (%d) reached without final answer", MAX_ITERATIONS)
    return "Task could not be completed within the allowed number of steps. Please try again or break the task into smaller parts."
