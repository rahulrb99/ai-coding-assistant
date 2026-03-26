"""
run_shell tool — Person 2
"""
from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict

from .base import Tool


def _kill_tree(pid: int) -> None:
    """Kill a process and all its children (cross-platform)."""
    if platform.system() == "Windows":
        subprocess.run(
            f"taskkill /F /T /PID {pid}",
            shell=True,
            capture_output=True,
        )
    else:
        try:
            import signal
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass


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
            # Use Popen so we control kill+drain on timeout, avoiding the double
            # communicate() hang that subprocess.run() does internally on TimeoutExpired.
            kwargs: Dict[str, Any] = {
                "shell": True,
                "cwd": str(self.workspace_root),
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
            }
            # On POSIX, put the process in its own group so we can kill the whole tree
            if platform.system() != "Windows":
                kwargs["start_new_session"] = True
            proc = subprocess.Popen(command, **kwargs)
            try:
                stdout_data, stderr_data = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Kill the entire process tree so child processes don't keep pipes open
                _kill_tree(proc.pid)
                try:
                    stdout_data, stderr_data = proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout_data, stderr_data = "", ""
                output = (
                    stdout_data + ("\n" if stdout_data and stderr_data else "") + stderr_data
                ).strip()
                return self.error(
                    f"Command timed out after {timeout}s "
                    f"(server/watcher process). Partial output:\n{self._truncate(output)}"
                )
        except KeyboardInterrupt:
            return self.error("Command interrupted by user.")
        except PermissionError:
            return self.error("Permission denied.")
        except OSError as e:
            return self.error(f"OS error: {e}")

        # Map Popen result onto a completed-process-like namespace for the code below
        class _Result:
            returncode = proc.returncode
            stdout = stdout_data
            stderr = stderr_data

        completed = _Result()

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
