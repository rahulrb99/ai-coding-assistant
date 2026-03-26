"""
Tests for Person 1 components:
  - config/settings.py
  - agent/agent_loop.py
  - agent/prompt_builder.py
  - cli/interface.py

Run: pytest tests/test_person1.py -v
"""
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers / Mocks
# ---------------------------------------------------------------------------

class _MockProvider:
    def __init__(self, responses):
        """responses: list of dicts returned in order."""
        self._responses = iter(responses)

    def generate(self, messages, tools):
        try:
            return next(self._responses)
        except StopIteration:
            return {"content": "done", "tool_call": None}


class _MockExecutor:
    def __init__(self, result=None):
        self._result = result or {"status": "success", "tool": "read_file", "output": "file content"}
        self.calls = []

    def execute(self, tool_name, arguments):
        self.calls.append((tool_name, arguments))
        return self._result


class _MockMemory:
    def __init__(self):
        self.history = []

    def add_user_message(self, content):
        self.history.append({"role": "user", "content": content})

    def add_assistant_message(self, content):
        self.history.append({"role": "assistant", "content": content})

    def add_raw_message(self, message: dict):
        self.history.append(message)

    def get_history(self):
        return self.history


class _MockRegistry:
    def get_tool_schemas(self):
        return [{"name": "read_file", "description": "Read a file", "schema": {}}]


class _MockPromptBuilder:
    def build(self, system_prompt, tools, history, user_input):
        return [{"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}]


# ---------------------------------------------------------------------------
# config/settings.py
# ---------------------------------------------------------------------------

class TestSettings:

    def test_loads_required_vars(self, monkeypatch):
        # Set env vars directly (avoids load_dotenv caching issues in test env)
        monkeypatch.setenv("MODEL_PROVIDER", "groq")
        monkeypatch.setenv("MODEL_NAME", "llama-3.1-8b-instant")
        monkeypatch.setenv("GROQ_API_KEY", "test123")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with patch("config.settings.load_dotenv"):
            from config.settings import get_settings
            settings = get_settings()

        assert settings["model_provider"] == "groq"
        assert settings["model_name"] == "llama-3.1-8b-instant"
        assert settings["api_key"] == "test123"

    def test_raises_if_model_provider_missing(self, monkeypatch):
        for k in ("MODEL_PROVIDER", "MODEL_NAME"):
            monkeypatch.delenv(k, raising=False)

        # Patch load_dotenv to do nothing (no .env file)
        with patch("config.settings.load_dotenv"):
            from config.settings import get_settings
            with pytest.raises(ValueError, match="MODEL_PROVIDER"):
                get_settings()

    def test_raises_if_model_name_missing(self, monkeypatch):
        monkeypatch.setenv("MODEL_PROVIDER", "groq")
        monkeypatch.delenv("MODEL_NAME", raising=False)

        with patch("config.settings.load_dotenv"):
            from config.settings import get_settings
            with pytest.raises(ValueError, match="MODEL_NAME"):
                get_settings()

    def test_defaults_execution_mode_to_auto(self, monkeypatch):
        monkeypatch.setenv("MODEL_PROVIDER", "groq")
        monkeypatch.setenv("MODEL_NAME", "llama-3.1-8b-instant")
        monkeypatch.delenv("EXECUTION_MODE", raising=False)

        with patch("config.settings.load_dotenv"):
            from config.settings import get_settings
            settings = get_settings()
            assert settings["execution_mode"] == "auto"

    def test_invalid_execution_mode_defaults_to_auto(self, monkeypatch):
        monkeypatch.setenv("MODEL_PROVIDER", "groq")
        monkeypatch.setenv("MODEL_NAME", "llama-3.1-8b-instant")
        monkeypatch.setenv("EXECUTION_MODE", "banana")

        with patch("config.settings.load_dotenv"):
            from config.settings import get_settings
            settings = get_settings()
            assert settings["execution_mode"] == "auto"

    def test_openai_provider_loads_openai_key(self, monkeypatch):
        monkeypatch.setenv("MODEL_PROVIDER", "openai")
        monkeypatch.setenv("MODEL_NAME", "gpt-4o-mini")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-key")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        with patch("config.settings.load_dotenv"):
            from config.settings import get_settings
            settings = get_settings()
            assert settings["api_key"] == "sk-openai-key"


# ---------------------------------------------------------------------------
# agent/agent_loop.py
# ---------------------------------------------------------------------------

class TestAgentLoop:

    def _make_loop(self, responses):
        from agent.agent_loop import run_agent_loop
        return run_agent_loop, _MockProvider(responses), _MockExecutor(), _MockMemory(), _MockPromptBuilder(), _MockRegistry()

    def test_returns_final_content_when_no_tool_call(self):
        from agent.agent_loop import run_agent_loop

        provider = _MockProvider([{"content": "Hello user!", "tool_call": None}])
        result = run_agent_loop(
            user_input="say hi",
            provider=provider,
            executor=_MockExecutor(),
            memory=_MockMemory(),
            prompt_builder=_MockPromptBuilder(),
            tool_registry=_MockRegistry(),
        )
        assert result == "Hello user!"

    def test_calls_tool_then_returns_final(self):
        from agent.agent_loop import run_agent_loop

        executor = _MockExecutor()
        provider = _MockProvider([
            {"content": None, "tool_call": {"name": "read_file", "arguments": {"path": "app.py"}}},
            {"content": "I read the file. It looks good.", "tool_call": None},
        ])
        memory = _MockMemory()

        result = run_agent_loop(
            user_input="read app.py",
            provider=provider,
            executor=executor,
            memory=memory,
            prompt_builder=_MockPromptBuilder(),
            tool_registry=_MockRegistry(),
        )

        assert result == "I read the file. It looks good."
        assert len(executor.calls) == 1
        assert executor.calls[0] == ("read_file", {"path": "app.py"})

    def test_tool_result_added_to_memory(self):
        from agent.agent_loop import run_agent_loop

        memory = _MockMemory()
        provider = _MockProvider([
            {"content": None, "tool_call": {"name": "read_file", "arguments": {"path": "x.py"}}},
            {"content": "Done.", "tool_call": None},
        ])

        run_agent_loop(
            user_input="read x.py",
            provider=provider,
            executor=_MockExecutor(),
            memory=memory,
            prompt_builder=_MockPromptBuilder(),
            tool_registry=_MockRegistry(),
        )

        roles = [m["role"] for m in memory.get_history()]
        # Proper OpenAI function-calling format:
        # user (original), assistant (with tool_calls), tool (result), assistant (final)
        assert "tool" in roles, "Tool result must be stored with role='tool'"
        assert roles.count("assistant") >= 1
        tool_msgs = [m for m in memory.get_history() if m["role"] == "tool"]
        assert len(tool_msgs) == 1
        assert "tool_call_id" in tool_msgs[0]

    def test_returns_error_message_after_max_iterations(self):
        from agent.agent_loop import run_agent_loop, MAX_ITERATIONS

        # Always return a tool_call so the loop never terminates
        provider = _MockProvider([
            {"content": None, "tool_call": {"name": "read_file", "arguments": {}}}
            for _ in range(MAX_ITERATIONS + 5)
        ])

        result = run_agent_loop(
            user_input="loop forever",
            provider=provider,
            executor=_MockExecutor(),
            memory=_MockMemory(),
            prompt_builder=_MockPromptBuilder(),
            tool_registry=_MockRegistry(),
        )

        assert "could not be completed" in result.lower()

    def test_handles_provider_exception(self):
        from agent.agent_loop import run_agent_loop

        class _CrashProvider:
            def generate(self, messages, tools):
                raise RuntimeError("API timeout")

        result = run_agent_loop(
            user_input="do something",
            provider=_CrashProvider(),
            executor=_MockExecutor(),
            memory=_MockMemory(),
            prompt_builder=_MockPromptBuilder(),
            tool_registry=_MockRegistry(),
        )
        assert "error" in result.lower()

    def test_retries_on_transient_error(self):
        """Provider fails twice then succeeds — loop should return final answer."""
        from agent.agent_loop import run_agent_loop
        from unittest.mock import patch

        call_count = {"n": 0}

        class _FlakyProvider:
            def generate(self, messages, tools):
                call_count["n"] += 1
                if call_count["n"] < 3:
                    raise RuntimeError("transient failure")
                return {"content": "finally worked", "tool_call": None}

        # Patch time.sleep so tests don't actually wait
        with patch("agent.agent_loop.time.sleep"):
            result = run_agent_loop(
                user_input="do something",
                provider=_FlakyProvider(),
                executor=_MockExecutor(),
                memory=_MockMemory(),
                prompt_builder=_MockPromptBuilder(),
                tool_registry=_MockRegistry(),
            )

        assert result == "finally worked"
        assert call_count["n"] == 3

    def test_rate_limit_error_surfaces_friendly_message(self):
        """After MAX_RETRIES exhausted on a 429, returns a human-friendly message."""
        from agent.agent_loop import run_agent_loop, MAX_RETRIES
        from unittest.mock import patch

        class _RateLimitProvider:
            def generate(self, messages, tools):
                raise RuntimeError("Error code: 429 - rate_limit_exceeded. Try again in 60s.")

        with patch("agent.agent_loop.time.sleep"):
            result = run_agent_loop(
                user_input="do something",
                provider=_RateLimitProvider(),
                executor=_MockExecutor(),
                memory=_MockMemory(),
                prompt_builder=_MockPromptBuilder(),
                tool_registry=_MockRegistry(),
            )

        assert "rate limit" in result.lower()
        assert "retry" in result.lower() or "wait" in result.lower()

    def test_empty_content_returns_empty_string(self):
        from agent.agent_loop import run_agent_loop

        provider = _MockProvider([{"content": "", "tool_call": None}])
        result = run_agent_loop(
            user_input="hi",
            provider=provider,
            executor=_MockExecutor(),
            memory=_MockMemory(),
            prompt_builder=_MockPromptBuilder(),
            tool_registry=_MockRegistry(),
        )
        assert result == ""

    def test_user_input_added_to_memory(self):
        from agent.agent_loop import run_agent_loop

        memory = _MockMemory()
        provider = _MockProvider([{"content": "ok", "tool_call": None}])
        run_agent_loop(
            user_input="hello world",
            provider=provider,
            executor=_MockExecutor(),
            memory=memory,
            prompt_builder=_MockPromptBuilder(),
            tool_registry=_MockRegistry(),
        )

        user_msgs = [m for m in memory.get_history() if m["role"] == "user"]
        assert any("hello world" in str(m["content"]) for m in user_msgs)


# ---------------------------------------------------------------------------
# cli/interface.py
# ---------------------------------------------------------------------------

class TestCLIInterface:

    def test_display_tool_log_does_not_crash(self):
        from cli.interface import display_tool_log
        # Just check it runs without error
        display_tool_log("read_file", "reading app.py")

    def test_display_response_does_not_crash(self):
        from cli.interface import display_response
        display_response("Here is the result.")

    def test_display_error_does_not_crash(self):
        from cli.interface import display_error
        display_error("Something went wrong.")

    def test_run_repl_exits_on_quit(self):
        from cli.interface import run_repl

        agent_calls = []

        def mock_agent(user_input, on_stream_chunk=None, on_usage=None):
            agent_calls.append(user_input)
            return "response"

        inputs = iter(["hello", "quit"])
        with patch("cli.interface.console") as mock_console:
            mock_console.input.side_effect = lambda _: next(inputs)
            run_repl(mock_agent)

        assert "hello" in agent_calls

    def test_run_repl_handles_keyboard_interrupt(self):
        from cli.interface import run_repl

        with patch("cli.interface.console") as mock_console:
            mock_console.input.side_effect = KeyboardInterrupt
            # Should exit cleanly without raising
            run_repl(lambda x, on_stream_chunk=None, on_usage=None: "ok")

    def test_run_repl_skips_empty_input(self):
        from cli.interface import run_repl

        agent_calls = []
        inputs = iter(["", "hello", "exit"])

        def mock_agent(user_input, on_stream_chunk=None, on_usage=None):
            agent_calls.append(user_input)
            return "ok"

        with patch("cli.interface.console") as mock_console:
            mock_console.input.side_effect = lambda _: next(inputs)
            run_repl(mock_agent)

        assert agent_calls == ["hello"]


# ---------------------------------------------------------------------------
# agent/prompt_builder.py
# ---------------------------------------------------------------------------

class TestPromptBuilder:

    def _history(self, n: int) -> list:
        """Build a dummy history of n alternating user/assistant messages."""
        history = []
        for i in range(n):
            role = "user" if i % 2 == 0 else "assistant"
            history.append({"role": role, "content": f"msg {i}"})
        return history

    def test_first_message_is_always_system(self):
        from agent.prompt_builder import build
        messages = build("You are a helpful AI.", [], self._history(3), "hello")
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful AI."

    def test_history_appended_after_system(self):
        from agent.prompt_builder import build
        history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
        messages = build("system", [], history, "next")
        assert messages[1] == {"role": "user", "content": "hi"}
        assert messages[2] == {"role": "assistant", "content": "hello"}

    def test_empty_history_returns_only_system(self):
        from agent.prompt_builder import build
        messages = build("sys", [], [], "hello")
        assert len(messages) == 1
        assert messages[0]["role"] == "system"

    def test_history_truncated_to_max_window(self):
        from agent.prompt_builder import build, MAX_HISTORY_MESSAGES
        # Build history larger than the max window
        large_history = self._history(MAX_HISTORY_MESSAGES + 10)
        messages = build("sys", [], large_history, "new input")
        # System + MAX_HISTORY_MESSAGES
        assert len(messages) == MAX_HISTORY_MESSAGES + 1

    def test_short_history_not_truncated(self):
        from agent.prompt_builder import build
        history = self._history(5)
        messages = build("sys", [], history, "hi")
        # system + 5 history messages
        assert len(messages) == 6

    def test_truncation_keeps_most_recent_messages(self):
        from agent.prompt_builder import build, MAX_HISTORY_MESSAGES
        large_history = self._history(MAX_HISTORY_MESSAGES + 5)
        messages = build("sys", [], large_history, "hi")
        # The last message in messages (excluding system) should be the last in history
        assert messages[-1] == large_history[-1]

    def test_tools_not_embedded_in_messages(self):
        from agent.prompt_builder import build
        tools = [{"name": "read_file", "description": "read", "schema": {}}]
        messages = build("sys", tools, [], "hi")
        # No message should contain tool definitions
        for m in messages:
            assert "read_file" not in str(m.get("content", ""))

    def test_returns_list_of_dicts(self):
        from agent.prompt_builder import build
        messages = build("sys", [], self._history(2), "hi")
        assert isinstance(messages, list)
        for m in messages:
            assert isinstance(m, dict)
            assert "role" in m
            assert "content" in m
