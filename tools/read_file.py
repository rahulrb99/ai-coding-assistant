"""
read_file tool — Person 2
"""
from typing import Any, Dict


class ReadFileTool:
    """Read file contents."""

    name = "read_file"
    description = "Read the contents of a file at the given path."
    schema = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "File path"}},
        "required": ["path"],
    }

    def execute(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        # TODO: Validate path within workspace_root
        # TODO: Read file, return {"status": "success", "output": content}
        # TODO: On error: {"status": "error", "message": "..."}
        pass
