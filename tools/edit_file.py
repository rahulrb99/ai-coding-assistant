"""
edit_file tool — Person 2
Block-based search/replace. Normalized matching: exact first, then whitespace-normalized.
"""
from typing import Any, Dict


class EditFileTool:
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

    def execute(
        self, path: str, search_block: str, replace_block: str, **kwargs: Any
    ) -> Dict[str, Any]:
        # TODO: 1. Exact match first
        # TODO: 2. If not found, normalize whitespace and try again
        # TODO: 3. Apply replacement, preserve original whitespace
        # TODO: 4. If still not found: {"status": "error", "message": "search_block not found"}
        pass
