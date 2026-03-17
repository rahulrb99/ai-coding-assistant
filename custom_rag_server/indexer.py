"""
RAG Indexer — Person 5
Load LangChain docs, split, embed, store in Chroma.
"""
from pathlib import Path
from typing import List


def index_documentation(docs_path: Path, chroma_path: Path) -> None:
    """
    Load docs, split into chunks, embed, store in Chroma.
    Run once; Chroma persists.
    """
    # TODO: DirectoryLoader, TextLoader
    # TODO: RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200)
    # TODO: HuggingFaceEmbeddings (all-MiniLM-L6-v2)
    # TODO: Chroma.from_documents()
    pass
