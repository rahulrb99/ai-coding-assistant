"""
search_codebase tool — Person 3
Use ripgrep if available, else Python regex.
"""
from typing import Any, Dict


class SearchCodebaseTool:
    """Search the codebase. Ripgrep preferred, regex fallback."""

    name = "search_codebase"
    description = "Search the codebase for a pattern. Uses ripgrep or regex."
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search pattern or query"},
        },
        "required": ["query"],
    }

    def execute(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        # TODO: Try ripgrep first
        # TODO: Fallback to Python regex if ripgrep unavailable
        # TODO: Return matches with file path and line
        pass
