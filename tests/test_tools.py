"""Tests for tool registry, workspace sandbox, and Safe Mode."""
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.executor import ToolExecutor
from tools.registry import ToolRegistry
from tools.write_file import WriteFileTool


@pytest.fixture
def workspace():
    # Avoid pytest's tmp_path on this machine: pytest-of-<user> is not writable.
    root = Path(tempfile.mkdtemp(prefix="vertex-ws-"))
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _executor(workspace: Path, *, safe_mode: bool) -> ToolExecutor:
    registry = ToolRegistry()
    registry.register(WriteFileTool(workspace_root=str(workspace)))
    return ToolExecutor(registry=registry, workspace_root=str(workspace), safe_mode=safe_mode)


class TestToolRegistry:
    def test_register_and_lookup(self):
        registry = ToolRegistry()
        tool = WriteFileTool(workspace_root=".")
        registry.register(tool)
        assert registry.get_tool("write_file") is tool
        assert "write_file" in registry.list_tools()
        schemas = registry.get_tool_schemas()
        assert schemas[0]["name"] == "write_file"
        assert "path" in schemas[0]["schema"]["required"]

    def test_reject_duplicate_names(self):
        registry = ToolRegistry()
        registry.register(WriteFileTool(workspace_root="."))
        try:
            registry.register(WriteFileTool(workspace_root="."))
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "already registered" in str(exc)


class TestToolExecutorSandbox:
    def test_unknown_tool(self, workspace):
        result = _executor(workspace, safe_mode=False).execute("not_a_tool", {})
        assert result["status"] == "error"
        assert "Unknown tool" in result["message"]

    def test_missing_required_params(self, workspace):
        result = _executor(workspace, safe_mode=False).execute("write_file", {"path": "a.txt"})
        assert result["status"] == "error"
        assert "content" in result["message"]

    def test_rejects_absolute_path(self, workspace):
        outside = Path.cwd() / "outside.txt"
        result = _executor(workspace, safe_mode=False).execute(
            "write_file",
            {"path": str(outside), "content": "nope"},
        )
        assert result["status"] == "error"
        assert "relative" in result["message"].lower()
        assert not outside.exists()

    def test_rejects_path_escape(self, workspace):
        result = _executor(workspace, safe_mode=False).execute(
            "write_file",
            {"path": "../escape.txt", "content": "nope"},
        )
        assert result["status"] == "error"
        assert "escapes" in result["message"].lower()
        assert not (workspace.parent / "escape.txt").exists()

    def test_writes_inside_workspace(self, workspace):
        result = _executor(workspace, safe_mode=False).execute(
            "write_file",
            {"path": "nested/ok.txt", "content": "hello"},
        )
        assert result["status"] == "success"
        assert (workspace / "nested" / "ok.txt").read_text(encoding="utf-8") == "hello"


class TestSafeMode:
    def test_blocks_write_when_user_declines(self, workspace):
        with patch("tools.executor.Confirm.ask", return_value=False):
            result = _executor(workspace, safe_mode=True).execute(
                "write_file",
                {"path": "blocked.txt", "content": "x"},
            )
        assert result["status"] == "error"
        assert "Cancelled" in result["message"]
        assert not (workspace / "blocked.txt").exists()

    def test_allows_write_when_user_confirms(self, workspace):
        with patch("tools.executor.Confirm.ask", return_value=True):
            result = _executor(workspace, safe_mode=True).execute(
                "write_file",
                {"path": "allowed.txt", "content": "ok"},
            )
        assert result["status"] == "success"
        assert (workspace / "allowed.txt").read_text(encoding="utf-8") == "ok"

    def test_auto_mode_skips_prompt(self, workspace):
        with patch("tools.executor.Confirm.ask") as ask:
            result = _executor(workspace, safe_mode=False).execute(
                "write_file",
                {"path": "auto.txt", "content": "go"},
            )
        ask.assert_not_called()
        assert result["status"] == "success"
