"""
search_codebase tool — Person 3
Use ripgrep if available, else Python regex.
"""
from __future__ import annotations

import fnmatch
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .base import Tool


class SearchCodebaseTool(Tool):
    """Search the codebase. Ripgrep preferred, regex fallback."""

    name = "search_codebase"
    description = "Search the codebase for a pattern. Uses ripgrep or regex."
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search pattern or query"},
            "regex": {"type": "boolean", "description": "Treat query as regex (default false)"},
            "max_results": {"type": "integer", "description": "Maximum matches to return (default 50)"},
            "file_glob": {"type": "string", "description": "Optional file glob filter, e.g. '*.py'"},
        },
        "required": ["query"],
    }

    _DEFAULT_MAX_RESULTS = 50
    _SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build", ".pytest_cache"}

    def __init__(self, workspace_root: str = "./workspace"):
        self.workspace_root = Path(workspace_root).resolve()

    def _iter_files(self) -> Iterable[Path]:
        for root, dirs, files in os.walk(self.workspace_root):
            # prune
            dirs[:] = [d for d in dirs if d not in self._SKIP_DIRS]
            for f in files:
                yield Path(root) / f

    def _matches_glob(self, path: Path, file_glob: Optional[str]) -> bool:
        if not file_glob:
            return True
        # Support simple patterns like "*.py" across the whole repo.
        return fnmatch.fnmatch(path.name, file_glob) or fnmatch.fnmatch(str(path.relative_to(self.workspace_root)), file_glob)

    def _try_ripgrep(self, query: str, regex: bool, max_results: int, file_glob: Optional[str]) -> Optional[List[str]]:
        if shutil.which("rg") is None:
            return None

        cmd: List[str] = ["rg", "--no-heading", "--line-number", "--color", "never", "--text"]
        if not regex:
            cmd.append("--fixed-string")
        if file_glob:
            cmd.extend(["--glob", file_glob])
        cmd.extend(["--max-count", str(max_results)])
        cmd.extend([query, str(self.workspace_root)])

        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            return None

        # rg returns 0 when matches found, 1 when no matches, 2 on error
        if p.returncode == 2:
            return None

        lines = [ln for ln in (p.stdout or "").splitlines() if ln.strip()]
        # Convert absolute paths to workspace-relative for consistency
        normalized: List[str] = []
        for ln in lines:
            # typical: /abs/path/file.py:12:content
            parts = ln.split(":", 2)
            if len(parts) < 3:
                continue
            abs_path, line_no, content = parts[0], parts[1], parts[2]
            try:
                rel = Path(abs_path).resolve().relative_to(self.workspace_root)
                normalized.append(f"{rel.as_posix()}:{line_no}:{content}")
            except Exception:
                normalized.append(ln)
        return normalized[:max_results]

    def _python_search(self, query: str, regex: bool, max_results: int, file_glob: Optional[str]) -> List[str]:
        pattern = re.compile(query) if regex else None
        results: List[str] = []

        for path in self._iter_files():
            try:
                if not self._matches_glob(path, file_glob):
                    continue
                # Ensure within workspace_root (defense-in-depth)
                resolved = path.resolve()
                resolved.relative_to(self.workspace_root)
            except Exception:
                continue

            try:
                text = resolved.read_text(encoding="utf-8", errors="strict")
            except (UnicodeDecodeError, PermissionError, OSError):
                continue

            rel = resolved.relative_to(self.workspace_root).as_posix()
            for i, line in enumerate(text.splitlines(), start=1):
                ok = False
                if regex:
                    ok = bool(pattern.search(line)) if pattern else False
                else:
                    ok = query in line
                if ok:
                    results.append(f"{rel}:{i}:{line}")
                    if len(results) >= max_results:
                        return results
        return results

    def execute(
        self,
        query: str,
        regex: bool = False,
        max_results: int = _DEFAULT_MAX_RESULTS,
        file_glob: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        try:
            if not isinstance(query, str) or query == "":
                return self.error("query must be a non-empty string.")
            if not isinstance(max_results, int) or max_results <= 0:
                return self.error("max_results must be a positive integer.")

            rg_results = self._try_ripgrep(query=query, regex=regex, max_results=max_results, file_glob=file_glob)
            if rg_results is not None:
                output = "\n".join(rg_results)
                return self.success(output)

            py_results = self._python_search(query=query, regex=regex, max_results=max_results, file_glob=file_glob)
            return self.success("\n".join(py_results))
        except re.error as e:
            return self.error(f"Invalid regex: {e}")
        except Exception as e:
            return self.error(str(e))
