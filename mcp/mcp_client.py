"""
MCP Client — Person 4
Connect to MCP servers, discover tools, wrap and register in ToolRegistry.
"""
import asyncio
import concurrent.futures
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.sse import sse_client

from tools.base import Tool

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_LOG_PREFIX = "[MCP]"

_logs_dir = Path(__file__).parent.parent / ".logs"
_logs_dir.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("mcp_client")

_file_handler = logging.FileHandler(_logs_dir / "mcp_client.log")
_file_handler.setLevel(logging.DEBUG)
_logger.addHandler(_file_handler)


def _log(msg: str) -> None:
    _logger.info(f"{_LOG_PREFIX} {msg}")


def _warn(msg: str) -> None:
    _logger.warning(f"{_LOG_PREFIX} {msg}")


def _error_log(msg: str) -> None:
    _logger.error(f"{_LOG_PREFIX} {msg}")


# ---------------------------------------------------------------------------
# _AsyncBridge — singleton persistent event loop on a daemon thread
# ---------------------------------------------------------------------------

class _AsyncBridge:
    """Bridges synchronous callers to async MCP SDK calls."""

    _instance: Optional["_AsyncBridge"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "_AsyncBridge":
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._loop = asyncio.new_event_loop()
                t = threading.Thread(
                    target=inst._loop.run_forever,
                    name="mcp-event-loop",
                    daemon=True,
                )
                t.start()
                inst._thread = t
                cls._instance = inst
        return cls._instance

    def run(self, coro: Any, timeout: float = 30.0) -> Any:
        """Submit *coro* to the background loop and block until done."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)


_bridge = _AsyncBridge()


# ---------------------------------------------------------------------------
# _MCPServerConnection — one server, reconnect-on-failure
# ---------------------------------------------------------------------------

class _MCPServerConnection:
    """Manages a single MCP server connection with lazy connect and reconnect."""

    def __init__(
        self,
        server_label: str,
        transport: str,
        command: Optional[str] = None,
        args: Optional[List[Any]] = None,
        env: Optional[Dict[str, str]] = None,
        url: Optional[str] = None,
    ) -> None:
        self._label = server_label
        self._transport = transport  # "stdio" or "sse"
        self._command = command
        self._args = [str(a) for a in (args or [])]
        self._env = env
        self._url = url
        self._session: Optional[ClientSession] = None
        self._lock = threading.Lock()
        # Keep a reference to context managers so they stay alive
        self._cm_stack: List[Any] = []

    async def _connect_async(self) -> ClientSession:
        """Open transport + ClientSession + initialize(). Returns session."""
        # Drop any stale context-manager references (anyio cancel scopes cannot
        # be exited from a different coroutine, so we just discard them and let
        # the OS reclaim the underlying subprocesses).
        self._cm_stack = []

        if self._transport == "stdio":
            params = StdioServerParameters(
                command=self._command,
                args=self._args,
                env=self._env,
            )
            cm = stdio_client(params)
        elif self._transport == "sse":
            cm = sse_client(self._url)
        else:
            raise ValueError(f"Unknown transport: {self._transport}")

        read_stream, write_stream = await cm.__aenter__()
        self._cm_stack.append(cm)

        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        self._cm_stack.append(session)
        await session.initialize()
        _log(f"Connected to server '{self._label}' via {self._transport}")
        return session

    def get_session(self) -> ClientSession:
        """Return current session, connecting if necessary. Thread-safe."""
        with self._lock:
            if self._session is None:
                self._session = _bridge.run(self._connect_async())
            return self._session

    def invalidate(self) -> None:
        """Mark session invalid so next call triggers reconnect."""
        with self._lock:
            self._session = None

    async def _call_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        session = self.get_session()
        result = await session.call_tool(tool_name, arguments)
        parts: List[str] = []
        for item in result.content:
            text = getattr(item, "text", None)
            if text is not None:
                parts.append(str(text))
        return "\n".join(parts)

    def call_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Synchronous entry point for tool execution."""
        return _bridge.run(self._call_tool_async(name, args))


# ---------------------------------------------------------------------------
# MCPToolWrapper — wraps one discovered MCP tool as a Tool
# ---------------------------------------------------------------------------

class MCPToolWrapper(Tool):
    """Wraps an MCP tool as a local Tool for use in ToolRegistry."""

    def __init__(
        self,
        mcp_name: str,
        mcp_description: str,
        mcp_schema: Dict[str, Any],
        connection: _MCPServerConnection,
    ) -> None:
        # Instance attributes (not class-level) — required by ToolRegistry.get_tool_schemas()
        self.name = mcp_name
        self.description = mcp_description
        self.schema = mcp_schema
        self._connection = connection

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        try:
            output = self._connection.call_tool(self.name, kwargs)
            return self.success(output)
        except TimeoutError as e:
            self._connection.invalidate()
            return self.error(f"MCP tool timed out: {e}")
        except Exception as e:
            self._connection.invalidate()
            return self.error(f"MCP tool error: {e}")


# ---------------------------------------------------------------------------
# _load_server_tools — discover and register tools for one server
# ---------------------------------------------------------------------------

def _load_server_tools(registry: Any, connection: _MCPServerConnection) -> int:
    """Connect to server, discover tools, register them. Returns count."""
    try:
        session = connection.get_session()
        # Allow extra time for servers that do one-time indexing/model downloads on boot.
        result = _bridge.run(session.list_tools(), timeout=120.0)
        tools = result.tools if hasattr(result, "tools") else result
        count = 0
        for tool in tools:
            tool_name = getattr(tool, "name", "")
            tool_desc = getattr(tool, "description", "")
            tool_schema = getattr(tool, "inputSchema", {}) or {}
            wrapper = MCPToolWrapper(
                mcp_name=tool_name,
                mcp_description=tool_desc,
                mcp_schema=tool_schema,
                connection=connection,
            )
            try:
                registry.register(wrapper)
                count += 1
                _log(f"Registered MCP tool '{tool_name}' from server '{connection._label}'")
            except ValueError as e:
                _warn(f"Skipping tool '{tool_name}' from '{connection._label}': {e}")
        return count
    except Exception as e:
        _error_log(f"Failed to load tools from server '{connection._label}': {e}")
        return 0


# ---------------------------------------------------------------------------
# load_tools — main orchestrator
# ---------------------------------------------------------------------------

def load_tools(registry: Any) -> None:
    """
    Connect to MCP servers (filesystem, Tavily/Context7, custom RAG).
    Discover tools, wrap as Tool objects, register in registry.
    All three servers are independent — failure of one never prevents others.
    """
    workspace_abs = Path(
        os.environ.get("WORKSPACE_ROOT", "./workspace")
    ).resolve()

    # ------------------------------------------------------------------
    # Server 1: Filesystem
    # ------------------------------------------------------------------
    try:
        fs_conn = _MCPServerConnection(
            server_label="filesystem",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", str(workspace_abs)],
        )
        n = _load_server_tools(registry, fs_conn)
        _log(f"Filesystem MCP server: {n} tools loaded")
    except Exception as e:
        _error_log(f"Filesystem MCP server setup failed: {e}")

    # ------------------------------------------------------------------
    # Server 2: Tavily (preferred) or Context7 (fallback) or skip
    # ------------------------------------------------------------------
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    mcp_tavily_url = os.environ.get("MCP_TAVILY_URL", "")
    mcp_context7_url = os.environ.get("MCP_CONTEXT7_URL", "")

    try:
        if tavily_key:
            if mcp_tavily_url:
                ext_conn = _MCPServerConnection(
                    server_label="tavily",
                    transport="sse",
                    url=mcp_tavily_url,
                )
            else:
                ext_conn = _MCPServerConnection(
                    server_label="tavily",
                    transport="stdio",
                    command="npx",
                    args=["-y", "tavily-mcp@latest"],
                    env={"TAVILY_API_KEY": tavily_key},
                )
            n = _load_server_tools(registry, ext_conn)
            _log(f"Tavily MCP server: {n} tools loaded")
        elif mcp_context7_url:
            ext_conn = _MCPServerConnection(
                server_label="context7",
                transport="sse",
                url=mcp_context7_url,
            )
            n = _load_server_tools(registry, ext_conn)
            _log(f"Context7 MCP server: {n} tools loaded")
        else:
            _warn("No external resource server configured. Continuing without.")
    except Exception as e:
        _error_log(f"External resource MCP server setup failed: {e}")

    # ------------------------------------------------------------------
    # Server 3: Custom RAG (Person 5)
    # ------------------------------------------------------------------
    mcp_rag_url = os.environ.get("MCP_RAG_SERVER_URL", "")

    try:
        if mcp_rag_url:
            rag_conn = _MCPServerConnection(
                server_label="custom_rag",
                transport="sse",
                url=mcp_rag_url,
            )
        else:
            rag_script = Path(__file__).parent.parent / "custom_rag_server" / "main.py"
            rag_conn = _MCPServerConnection(
                server_label="custom_rag",
                transport="stdio",
                command=sys.executable,
                args=[str(rag_script)],
            )
        n = _load_server_tools(registry, rag_conn)
        _log(f"Custom RAG MCP server: {n} tools loaded")
    except Exception as e:
        _error_log(f"Custom RAG MCP server setup failed: {e}")


# ---------------------------------------------------------------------------
# MCPClient — public API
# ---------------------------------------------------------------------------

class MCPClient:
    """MCP client. Connects to servers and loads tools."""

    def __init__(self, registry: Any) -> None:
        self.registry = registry
        # Populated after connect_and_load(): {"server_name": tool_count}
        self.server_stats: dict = {}

    def connect_and_load(self) -> None:
        """Connect to all servers and load tools into registry."""
        _log("MCPClient.connect_and_load() starting")
        # Snapshot tool list before loading to compute per-server deltas
        _before: set = set(self.registry.list_tools()) if hasattr(self.registry, "list_tools") else set()

        # Patch _load_server_tools to capture per-server counts
        import mcp.mcp_client as _self_mod
        _orig = _self_mod._load_server_tools

        _stats: dict = {}

        def _tracked(registry: Any, connection: Any) -> int:
            label = getattr(connection, "_label", "unknown")
            n = _orig(registry, connection)
            _stats[label] = n
            return n

        _self_mod._load_server_tools = _tracked
        try:
            load_tools(self.registry)
        finally:
            _self_mod._load_server_tools = _orig

        self.server_stats = _stats
        _log("MCPClient.connect_and_load() complete")
