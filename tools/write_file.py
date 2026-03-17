"""
write_file tool — Person 2
"""
from typing import Any, Dict


class WriteFileTool:
    """Write content to a file."""

    name = "write_file"
    description = "Write content to a file at the given path."
    schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
            "content": {"type": "string", "description": "File content"},
        },
        "required": ["path", "content"],
    }

    def execute(self, path: str, content: str, **kwargs: Any) -> Dict[str, Any]:
        # TODO: Validate path within workspace_root
        # TODO: Write file, return {"status": "success", "output": "..."}
        pass
