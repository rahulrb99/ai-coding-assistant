"""
Custom RAG MCP Server — Person 5
Indexes LangChain docs. HyDE. Exposes as MCP server.
"""
from custom_rag_server.indexer import index_documentation
from custom_rag_server.retriever import retrieve
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP('custom-rag-server')

# Docs can be .md or .mdx files inside langchain_docs/
LANGCHAIN_DOCS_PATH = Path('./langchain_docs')
CHROMA_DB_PATH = Path('./chroma_db')

@mcp.tool()
def query(query: str, top_k: int = 5) -> str:
    chunks = retrieve(query, top_k, CHROMA_DB_PATH)
    return "\n\n---\n\n".join(chunks)

def main() -> None:
    """MCP server entry point."""
    try:
        index_documentation(LANGCHAIN_DOCS_PATH, CHROMA_DB_PATH)
    except FileNotFoundError as exc:
        import sys
        print(f"[custom_rag] WARNING: {exc}", file=sys.stderr)
        print("[custom_rag] Server starting without indexed docs — query tool will return empty results.", file=sys.stderr)
    except Exception as exc:
        import sys
        print(f"[custom_rag] ERROR during indexing: {exc}", file=sys.stderr)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
