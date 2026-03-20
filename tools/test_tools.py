"""
test_tools.py
Tests for Person 2 (Dhruti) — Tool Registry, Executor, and all local tools.
Run with: pytest test_tools.py -v
"""

import pytest
from pathlib import Path

from tools.registry   import ToolRegistry
from tools.executor   import ToolExecutor
from tools.read_file  import ReadFileTool
from tools.write_file import WriteFileTool
from tools.edit_file  import EditFileTool
from tools.run_shell  import RunShellTool
from tools.search_codebase import SearchCodebaseTool


# Shared fixture: temp workspace
@pytest.fixture
def workspace(tmp_path):
    """Creates a real temporary workspace directory for each test."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def registry(workspace):
    """Registry pre-loaded with all 4 tools."""
    r = ToolRegistry()
    r.register(ReadFileTool(workspace_root=str(workspace)))
    r.register(WriteFileTool(workspace_root=str(workspace)))
    r.register(EditFileTool(workspace_root=str(workspace)))
    r.register(RunShellTool(workspace_root=str(workspace)))
    r.register(SearchCodebaseTool(workspace_root=str(workspace)))
    return r


@pytest.fixture
def executor(registry, workspace):
    """Executor in AUTO mode (no confirmation prompts during tests)."""
    return ToolExecutor(registry=registry, workspace_root=str(workspace), safe_mode=False)


# 1. ToolRegistry
class TestToolRegistry:

    def test_registers_four_tools(self, registry):
        assert len(registry) == 5

    def test_get_tool_returns_correct_instance(self, registry, workspace):
        tool = registry.get_tool("read_file")
        assert tool is not None
        assert tool.name == "read_file"

    def test_get_tool_unknown_returns_none(self, registry):
        assert registry.get_tool("nonexistent") is None

    def test_list_tools_contains_all(self, registry):
        names = registry.list_tools()
        assert set(names) == {"read_file", "write_file", "edit_file", "run_shell", "search_codebase"}

    def test_get_tool_schemas_returns_correct_keys(self, registry):
        schemas = registry.get_tool_schemas()
        assert len(schemas) == 5
        for s in schemas:
            assert "name" in s
            assert "description" in s
            assert "schema" in s

    def test_duplicate_registration_raises(self, workspace):
        r = ToolRegistry()
        r.register(ReadFileTool(workspace_root=str(workspace)))
        with pytest.raises(ValueError):
            r.register(ReadFileTool(workspace_root=str(workspace)))

    def test_empty_name_raises(self):
        class BadTool(ReadFileTool):
            name = ""
        r = ToolRegistry()
        with pytest.raises(ValueError):
            r.register(BadTool())



# 2. ToolExecutor
class TestToolExecutor:

    def test_unknown_tool_returns_error(self, executor):
        r = executor.execute("does_not_exist", {})
        assert r["status"] == "error"
        assert r["tool"] == "does_not_exist"

    def test_missing_required_param_returns_error(self, executor):
        # read_file requires "path"
        r = executor.execute("read_file", {})
        assert r["status"] == "error"
        assert r["tool"] == "read_file"

    def test_search_codebase_missing_query_returns_error(self, executor):
        r = executor.execute("search_codebase", {})
        assert r["status"] == "error"
        assert r["tool"] == "search_codebase"

    def test_path_traversal_blocked(self, executor):
        r = executor.execute("read_file", {"path": "../secret.txt"})
        assert r["status"] == "error"
        assert r["tool"] == "read_file"

    def test_set_safe_mode(self, executor):
        executor.set_safe_mode(True)
        assert executor.safe_mode is True
        executor.set_safe_mode(False)
        assert executor.safe_mode is False


# 3. ReadFileTool
class TestReadFileTool:

    def test_reads_file_successfully(self, executor, workspace):
        (workspace / "hello.py").write_text("print('hello')\n")
        tool = ReadFileTool(workspace_root=str(workspace))
        r = tool.execute(path="hello.py")
        assert r["status"] == "success"
        assert "print('hello')" in r["output"]

    def test_output_has_line_numbers(self, executor, workspace):
        (workspace / "numbered.py").write_text("line one\nline two\n")
        tool = ReadFileTool(workspace_root=str(workspace))
        r = tool.execute(path="numbered.py")
        assert r["status"] == "success"
        assert "1 | line one" in r["output"]
        assert "2 | line two" in r["output"]

    def test_missing_file_returns_error(self, executor):
        tool = ReadFileTool(workspace_root=str(Path.cwd()))
        r = tool.execute(path="does_not_exist.py")
        assert r["status"] == "error"

    def test_directory_returns_error(self, executor, workspace):
        (workspace / "mydir").mkdir()
        tool = ReadFileTool(workspace_root=str(workspace))
        r = tool.execute(path="mydir")
        assert r["status"] == "error"

    def test_path_traversal_blocked(self, executor):
        tool = ReadFileTool(workspace_root=str(workspace := Path(__file__).parent))
        r = tool.execute(path="../secret.txt")
        assert r["status"] == "error"

    def test_absolute_path_rejected(self, workspace):
        (workspace / "x.txt").write_text("hi\n")
        tool = ReadFileTool(workspace_root=str(workspace))
        r = tool.execute(path=str((workspace / "x.txt").resolve()))
        assert r["status"] == "error"

    def test_non_utf8_rejected(self, workspace):
        p = workspace / "bin.dat"
        p.write_bytes(b"\xff\xfe\x00\x00")
        tool = ReadFileTool(workspace_root=str(workspace))
        r = tool.execute(path="bin.dat")
        assert r["status"] == "error"



# 4. WriteFileTool
class TestWriteFileTool:

    def test_creates_new_file(self, executor, workspace):
        tool = WriteFileTool(workspace_root=str(workspace))
        r = tool.execute(path="new.py", content="x = 1\n")
        assert r["status"] == "success"
        assert (workspace / "new.py").read_text() == "x = 1\n"

    def test_overwrites_existing_file(self, executor, workspace):
        (workspace / "existing.py").write_text("old content\n")
        tool = WriteFileTool(workspace_root=str(workspace))
        tool.execute(path="existing.py", content="new content\n")
        assert (workspace / "existing.py").read_text() == "new content\n"

    def test_creates_parent_directories(self, executor, workspace):
        tool = WriteFileTool(workspace_root=str(workspace))
        r = tool.execute(path="sub/dir/deep.py", content="y = 2\n")
        assert r["status"] == "success"
        assert (workspace / "sub" / "dir" / "deep.py").exists()

    def test_path_traversal_blocked(self, executor):
        tool = WriteFileTool(workspace_root=str(Path(__file__).parent))
        r = tool.execute(path="../outside.py", content="bad")
        assert r["status"] == "error"

    def test_success_message_has_info(self, executor, workspace):
        tool = WriteFileTool(workspace_root=str(workspace))
        r = tool.execute(path="info.py", content="a = 1\nb = 2\n")
        assert r["status"] == "success"
        assert "info.py" in r["output"] or "Written" in r["output"] or "2" in r["output"]


# 5. EditFileTool
class TestEditFileTool:

    def test_exact_match_replaces_correctly(self, executor, workspace):
        (workspace / "edit.py").write_text(
            "def greet():\n    print('hello')\n"
        )
        tool = EditFileTool(workspace_root=str(workspace))
        r = tool.execute(
            path="edit.py",
            search_block="    print('hello')",
            replace_block="    print('hello, world!')",
        )
        assert r["status"] == "success"
        content = (workspace / "edit.py").read_text()
        assert "hello, world!" in content

    def test_exact_match_only_replaces_first_occurrence(self, executor, workspace):
        (workspace / "dup.py").write_text("x = 1\nx = 1\n")
        tool = EditFileTool(workspace_root=str(workspace))
        tool.execute(path="dup.py", search_block="x = 1", replace_block="x = 99")
        content = (workspace / "dup.py").read_text()
        assert content.count("x = 99") == 1
        assert content.count("x = 1") == 1

    def test_no_match_returns_error(self, executor, workspace):
        (workspace / "nomatch.py").write_text("def foo():\n    pass\n")
        tool = EditFileTool(workspace_root=str(workspace))
        r = tool.execute(
            path="nomatch.py",
            search_block="THIS DOES NOT EXIST",
            replace_block="anything",
        )
        assert r["status"] == "error"

    def test_no_match_error_has_helpful_tip(self, executor, workspace):
        (workspace / "tip.py").write_text("def foo():\n    pass\n")
        tool = EditFileTool(workspace_root=str(workspace))
        r = tool.execute(path="tip.py", search_block="MISSING BLOCK", replace_block="x")
        assert r["status"] == "error"
        # Should give a helpful message, not just "error"
        assert len(r["message"]) > 20

    def test_missing_file_returns_error(self, executor):
        tool = EditFileTool(workspace_root=str(Path.cwd()))
        r = tool.execute(path="ghost.py", search_block="anything", replace_block="anything")
        assert r["status"] == "error"

    def test_path_traversal_blocked(self, executor):
        tool = EditFileTool(workspace_root=str(Path(__file__).parent))
        r = tool.execute(
            path="../../etc/hosts",
            search_block="localhost",
            replace_block="hacked",
        )
        assert r["status"] == "error"

    def test_normalized_match_fallback(self, workspace):
        (workspace / "norm.py").write_text("print(  1  )\n")
        tool = EditFileTool(workspace_root=str(workspace))
        r = tool.execute(path="norm.py", search_block="print(1)", replace_block="print(2)")
        assert r["status"] == "success"
        assert (workspace / "norm.py").read_text() == "print(2)\n"


# 6. RunShellTool
class TestRunShellTool:

    def test_runs_simple_command(self, executor):
        tool = RunShellTool(workspace_root=str(Path.cwd()))
        r = tool.execute(command="echo hello_world")
        assert r["status"] == "success"
        assert "hello_world" in r["output"]

    def test_output_includes_exit_code(self, executor):
        tool = RunShellTool(workspace_root=str(Path.cwd()))
        r = tool.execute(command="echo done")
        assert r["status"] == "success"
        assert "[Exit code: 0]" in r["output"]

    def test_nonzero_exit_still_returns_success_status(self, executor):
        # Tool ran fine — agent should see output and reason about it
        tool = RunShellTool(workspace_root=str(Path.cwd()))
        r = tool.execute(command="exit 1")
        assert r["status"] == "success"
        assert "[Exit code: 1]" in r["output"]

    def test_blocks_dangerous_rm_command(self, executor):
        tool = RunShellTool(workspace_root=str(Path.cwd()))
        r = tool.execute(command="rm -rf /")
        assert r["status"] == "error"

    def test_timeout_returns_error(self, executor):
        tool = RunShellTool(workspace_root=str(Path.cwd()))
        r = tool.execute(command="sleep 60", timeout=1)
        assert r["status"] == "error"

    def test_runs_in_workspace_directory(self, executor, workspace):
        # Create a file in workspace, list it — should appear in output
        (workspace / "marker.txt").write_text("exists")
        tool = RunShellTool(workspace_root=str(workspace))
        r = tool.execute(command="ls")
        assert r["status"] == "success"
        assert "marker.txt" in r["output"]

    def test_captures_stderr(self, executor):
        # python -c with bad code writes to stderr
        tool = RunShellTool(workspace_root=str(Path.cwd()))
        r = tool.execute(command="python3 -c 'import nonexistent_module_xyz'")
        assert r["status"] == "success"  # tool ran fine
        assert "nonexistent_module_xyz" in r["output"] or "ModuleNotFoundError" in r["output"]

    def test_output_truncates(self, workspace):
        tool = RunShellTool(workspace_root=str(workspace))
        # Generate >8000 characters without external deps; python is allowed in test env.
        r = tool.execute(command="python3 -c 'print(\"a\"*9000)'")
        assert r["status"] == "success"
        assert len(r["output"]) <= 8200  # includes truncation marker + exit code
        assert "[Output truncated]" in r["output"]


# ═══════════════════════════════════════════════════════════════════════
# 7. SearchCodebaseTool
# ═══════════════════════════════════════════════════════════════════════

class TestSearchCodebaseTool:

    def test_finds_substring_match(self, workspace):
        (workspace / "a.py").write_text("print('hello')\n")
        tool = SearchCodebaseTool(workspace_root=str(workspace))
        r = tool.execute(query="hello")
        assert r["status"] == "success"
        assert "a.py:" in r["output"]

    def test_respects_file_glob(self, workspace):
        (workspace / "a.py").write_text("needle\n")
        (workspace / "b.txt").write_text("needle\n")
        tool = SearchCodebaseTool(workspace_root=str(workspace))
        r = tool.execute(query="needle", file_glob="*.py")
        assert r["status"] == "success"
        assert "a.py:" in r["output"]
        assert "b.txt:" not in r["output"]

    def test_regex_mode(self, workspace):
        (workspace / "r.py").write_text("value = 123\n")
        tool = SearchCodebaseTool(workspace_root=str(workspace))
        r = tool.execute(query=r"value\s*=\s*\d+", regex=True)
        assert r["status"] == "success"
        assert "r.py:" in r["output"]

    def test_max_results_limits_output(self, workspace):
        (workspace / "many.py").write_text("x\nx\nx\nx\nx\n")
        tool = SearchCodebaseTool(workspace_root=str(workspace))
        r = tool.execute(query="x", max_results=2)
        assert r["status"] == "success"
        assert len([ln for ln in r["output"].splitlines() if ln.strip()]) <= 2