"""
write_file tool — Person 2
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .base import Tool


class WriteFileTool(Tool):
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

    def __init__(self, workspace_root: str = "./workspace"):
        self.workspace_root = Path(workspace_root).resolve()

    def _resolve_workspace_path(self, path: str) -> Path:
        rel = Path(path)
        if rel.is_absolute():
            raise ValueError("Path must be relative to workspace_root (absolute paths are not allowed).")

        target = (self.workspace_root / rel).resolve()
        try:
            target.relative_to(self.workspace_root)
        except ValueError as e:
            raise ValueError("Path escapes workspace_root.") from e
        return target

    def execute(self, path: str, content: str, **kwargs: Any) -> Dict[str, Any]:
        try:
            target = self._resolve_workspace_path(path)
        except ValueError as e:
            return self.error(f"Security error: {e}")

        try:
            if target.exists() and target.is_dir():
                return self.error("Path is a directory, not a file.")

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            rel = target.relative_to(self.workspace_root)
            return self.success(f"Wrote {len(content)} characters to {rel.as_posix()}.")
        except PermissionError:
            return self.error("Permission denied.")
        except OSError as e:
            return self.error(f"OS error: {e}")
