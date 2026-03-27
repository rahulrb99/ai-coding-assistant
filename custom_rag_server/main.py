"""
Custom RAG MCP Server — Person 5
Indexes LangChain docs. HyDE. Exposes as MCP server.
"""
import logging
import os
import sys
from custom_rag_server.indexer import index_documentation
from custom_rag_server.retriever import retrieve
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP('custom-rag-server')

# Docs can be .md or .mdx files inside langchain_docs/
LANGCHAIN_DOCS_PATH = Path('./langchain_docs')
CHROMA_DB_PATH = Path('./chroma_db')
_INDEXED = False


def _ensure_indexed() -> None:
    """
    Index docs lazily so the stdio MCP server can start instantly.
    MCP clients call list_tools() immediately after spawn; doing heavy indexing
    before mcp.run() can cause the client to time out and report 'Connection closed'.
    """
    global _INDEXED
    if _INDEXED:
        return
    index_documentation(LANGCHAIN_DOCS_PATH, CHROMA_DB_PATH)
    _INDEXED = True

@mcp.tool()
def query(query: str, top_k: int = 5) -> str:
    try:
        _ensure_indexed()
    except Exception:
        # If indexing isn't ready, still allow the server to respond deterministically.
        return ""
    chunks = retrieve(query, top_k, CHROMA_DB_PATH)
    return "\n\n---\n\n".join(chunks)

def main() -> None:
    """MCP server entry point."""
    # IMPORTANT: stdio MCP transport uses stdout for JSON-RPC.
    # Any non-JSON output on stdout will break the connection and look like
    # "Connection closed" in the client. Force logs to stderr and silence noisy libs.
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stderr,
        force=True,
    )
    for name in (
        "chromadb",
        "posthog",
        "sentence_transformers",
        "transformers",
        "urllib3",
        "requests",
    ):
        logging.getLogger(name).setLevel(logging.ERROR)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
