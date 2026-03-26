"""
Custom RAG MCP Server — Person 5
Indexes LangChain docs. HyDE. Exposes as MCP server.
"""
from indexer import index_documentation
from retriever import retrieve
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP('custom-rag-server')

LANGCHAIN_DOCS_PATH = Path('./langchain_docs/src')
CHROMA_DB_PATH = Path('./chroma_db')

@mcp.tool()
def query(query: str, top_k: int = 5) -> str:
    chunks = retrieve(query, top_k, CHROMA_DB_PATH)
    return "\n\n---\n\n".join(chunks)

def main() -> None:
    """MCP server entry point."""
    # TODO: Load indexer, retriever
    # TODO: Expose query tool via MCP
    index_documentation(LANGCHAIN_DOCS_PATH, CHROMA_DB_PATH)

    mcp.run()


if __name__ == "__main__":
    main()
