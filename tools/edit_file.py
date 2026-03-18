"""
edit_file tool — Person 2
Block-based search/replace. Normalized matching: exact first, then whitespace-normalized.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Tuple

from .base import Tool


class EditFileTool(Tool):
    """Replace search_block with replace_block in file. Normalized matching."""

    name = "edit_file"
    description = "Replace the first matching block in a file. Uses normalized matching."
    schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
            "search_block": {"type": "string", "description": "Text to find"},
            "replace_block": {"type": "string", "description": "Text to replace with"},
        },
        "required": ["path", "search_block", "replace_block"],
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

    @staticmethod
    def _normalize_ws(s: str) -> str:
        # 1) Collapse whitespace runs
        s = re.sub(r"\s+", " ", s)
        # 2) Strip spaces just inside parentheses
        s = re.sub(r"\(\s+", "(", s)
        s = re.sub(r"\s+\)", ")", s)
        return s.strip()

    @staticmethod
    def _split_preserve_last_empty_line(text: str) -> Tuple[list[str], str]:
        # Returns (lines, newline) where newline is "\n" or "" based on original.
        # We keep replacement simple: read_text() normalizes newlines; we'll write "\n".
        newline = "\n" if text.endswith("\n") else ""
        return text.splitlines(), newline

    def execute(
        self, path: str, search_block: str, replace_block: str, **kwargs: Any
    ) -> Dict[str, Any]:
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
                original = target.read_text(encoding="utf-8", errors="strict")
            except UnicodeDecodeError:
                return self.error("Binary or non-UTF8 file cannot be edited.")
        except PermissionError:
            return self.error("Permission denied.")
        except OSError as e:
            return self.error(f"OS error: {e}")

        # 1) Exact match first
        if search_block in original:
            updated = original.replace(search_block, replace_block, 1)
            try:
                target.write_text(updated, encoding="utf-8")
            except PermissionError:
                return self.error("Permission denied.")
            except OSError as e:
                return self.error(f"OS error: {e}")
            return self.success("Replaced block (exact match).")

        # 2) Whitespace-normalized match fallback (line-windowed)
        file_lines, file_trailing_nl = self._split_preserve_last_empty_line(original)
        search_lines, _ = self._split_preserve_last_empty_line(search_block)

        if len(search_lines) == 0:
            return self.error(
                "search_block is empty. Tip: provide the exact text block you want to replace."
            )

        normalized_search = self._normalize_ws(search_block)
        n = len(search_lines)

        for start in range(0, max(0, len(file_lines) - n) + 1):
            window = "\n".join(file_lines[start : start + n])
            if self._normalize_ws(window) == normalized_search:
                new_lines = file_lines[:start] + replace_block.splitlines() + file_lines[start + n :]
                updated = "\n".join(new_lines) + file_trailing_nl
                try:
                    target.write_text(updated, encoding="utf-8")
                except PermissionError:
                    return self.error("Permission denied.")
                except OSError as e:
                    return self.error(f"OS error: {e}")
                return self.success(
                    "Replaced block (whitespace-normalized match). Tip: consider using an exact search_block next time for maximum reliability."
                )

        # 3) Neither match: helpful structured error
        tip = (
            "search_block not found.\n"
            "Tip: copy/paste the exact block from the file (include a few surrounding lines), "
            "or ensure your search_block has the same number of lines as in the file. "
            "This tool matches either exact text or a whitespace-normalized version (collapses spaces, trims inside parentheses)."
        )
        return self.error(tip)
