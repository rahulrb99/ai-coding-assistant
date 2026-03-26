"""
RAG Indexer — Person 5
Load LangChain docs, split, embed, store in Chroma.
"""
from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def index_documentation(docs_path: Path, chroma_path: Path) -> None:
    """
    Load docs, split into chunks, embed, store in Chroma.
    Run once; Chroma persists across restarts.
    """
    # Already indexed — skip
    if chroma_path.exists() and any(chroma_path.iterdir()):
        return

    if not docs_path.exists():
        raise FileNotFoundError(
            f"Documentation folder not found: {docs_path.resolve()}. "
            "Run 'python custom_rag_server/download_docs.py' first."
        )

    # Load both .md and .mdx — LangChain uses a mix across versions
    docs = []
    for pattern in ("**/*.mdx", "**/*.md"):
        loader = DirectoryLoader(
            path=str(docs_path),
            glob=pattern,
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
            recursive=True,
        )
        docs.extend(loader.load())

    if not docs:
        raise ValueError(
            f"No .md/.mdx files found in {docs_path.resolve()}. "
            "Re-run 'python custom_rag_server/download_docs.py'."
        )

    from langchain_text_splitters import RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    chunks = text_splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(model_name=_MODEL_NAME)
    vector_store = Chroma(
        collection_name="RAG-embedder",
        embedding_function=embeddings,
        persist_directory=str(chroma_path),
    )
    vector_store.add_documents(chunks)