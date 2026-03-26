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
    loader = DirectoryLoader(
        path=str(docs_path),
        glob="**/*.mdx",
        loader_cls=TextLoader,
        loader_kwargs={'encoding': 'utf-8'},
        recursive=True
    )

    docs = loader.load()
    
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

    chunks = text_splitter.split_documents(docs)

    vector_store.add_documents(chunks)