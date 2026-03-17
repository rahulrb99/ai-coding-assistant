"""
run_shell tool — Person 2
"""
import subprocess
from typing import Any, Dict


class RunShellTool:
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

    def execute(self, command: str, **kwargs: Any) -> Dict[str, Any]:
        # TODO: Validate cwd within workspace_root
        # TODO: subprocess.run, return stdout/stderr
        pass
