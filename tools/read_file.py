"""
read_file tool — Person 2
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .base import Tool


class ReadFileTool(Tool):
    """Read file contents."""

    name = "read_file"
    description = "Read the contents of a file at the given path."
    schema = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "File path"}},
        "required": ["path"],
    }

    def __init__(self, workspace_root: str = "./workspace"):
        self.workspace_root = Path(workspace_root).resolve()

    def _resolve_workspace_path(self, path: str) -> Path:
        # Treat incoming path as workspace-relative (never absolute)
        rel = Path(path)
        if rel.is_absolute():
            raise ValueError("Path must be relative to workspace_root (absolute paths are not allowed).")

        target = (self.workspace_root / rel).resolve()
        try:
            target.relative_to(self.workspace_root)
        except ValueError as e:
            raise ValueError("Path escapes workspace_root.") from e
        return target

    def execute(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        try:
            target = self._resolve_workspace_path(path)
        except ValueError as e:
            return self.error(f"Security error: {e}")

        try:
            if not target.exists():
                return self.error("File not found.")
            if target.is_dir():
                return self.error("Path is a directory, not a file.")

            try:
                raw = target.read_text(encoding="utf-8", errors="strict")
            except UnicodeDecodeError:
                return self.error("Binary or non-UTF8 file cannot be read.")

        except PermissionError:
            return self.error("Permission denied.")
        except OSError as e:
            return self.error(f"OS error: {e}")

        numbered_lines = []
        for i, line in enumerate(raw.splitlines(), start=1):
            numbered_lines.append(f"{i} | {line}")
        output = "\n".join(numbered_lines)
        return self.success(output)
