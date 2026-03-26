"""
RAG Indexer — Person 5
Load LangChain docs, split, embed, store in Chroma.
"""
from pathlib import Path
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader


def index_documentation(docs_path: Path, chroma_path: Path) -> None:
    """
    Load docs, split into chunks, embed, store in Chroma.
    Run once; Chroma persists.
    """
    # TODO: DirectoryLoader, TextLoader
    # TODO: RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200)
    # TODO: HuggingFaceEmbeddings (all-MiniLM-L6-v2)
    # TODO: Chroma.from_documents()
    embeddings = HuggingFaceEmbeddings()
    vector_store = Chroma(
        collection_name='RAG-embedder',
        embedding_function=embeddings,
        persist_directory=str(chroma_path)
    )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        overlap=200,
    )

    text_loader = TextLoader(
        path
    )

    loader = DirectoryLoader(
        path=str(docs_path),
        glob="**/*.txt",
        loader_cls=
    )
    pass
