"""MCP module."""
import sys
import os

_here = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_here)

# Extend __path__ to include the real mcp SDK directory so submodule imports
# like `from mcp.client.stdio import stdio_client` work even though the local
# mcp/ package normally shadows the installed SDK.
for _p in sys.path:
    _abs = os.path.abspath(_p) if _p not in ("", ".") else os.path.abspath(".")
    if _abs == os.path.abspath(_proj_root):
        continue
    _sdk_dir = os.path.join(_abs, "mcp")
    if os.path.isdir(_sdk_dir) and os.path.abspath(_sdk_dir) != _here:
        __path__.append(_sdk_dir)
        break
