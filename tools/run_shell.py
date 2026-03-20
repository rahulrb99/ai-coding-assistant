"""
run_shell tool — Person 2
"""
from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any, Dict

from .base import Tool


class RunShellTool(Tool):
    """Run a shell command."""

    name = "run_shell"
    description = "Execute a shell command."
    schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run"},
        },
        "required": ["command"],
    }

    _BLOCKLIST = ("rm -rf /", "mkfs", "shutdown", "reboot", "halt")

    def __init__(self, workspace_root: str = "./workspace"):
        self.workspace_root = Path(workspace_root).resolve()

    @staticmethod
    def _truncate(s: str, limit: int = 8000) -> str:
        if len(s) <= limit:
            return s
        return s[:limit] + "\n[Output truncated]"

    def execute(self, command: str, timeout: int = 30, **kwargs: Any) -> Dict[str, Any]:
        for banned in self._BLOCKLIST:
            if banned in command:
                return self.error(f"Blocked dangerous command pattern: {banned!r}")

        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            stdout = e.stdout or ""
            stderr = e.stderr or ""
            output = (stdout + ("\n" if stdout and stderr else "") + stderr).strip()
            output = self._truncate(output)
            return self.error(f"Command timed out after {timeout}s.\n{output}")
        except PermissionError:
            return self.error("Permission denied.")
        except OSError as e:
            return self.error(f"OS error: {e}")

        combined = ""
        if completed.stdout:
            combined += completed.stdout
        if completed.stderr:
            if combined and not combined.endswith("\n"):
                combined += "\n"
            combined += completed.stderr

        combined = combined.rstrip("\n")
        combined += f"\n[Exit code: {completed.returncode}]"
        combined = self._truncate(combined)

        # IMPORTANT: return success even on nonzero exit so agent can reason about failures
        return self.success(combined)
