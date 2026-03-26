"""
RAG Retriever — Person 5
HyDE: generate hypothetical answer, embed, retrieve similar chunks.
"""
from typing import List
import os
from groq import Groq
from custom_rag_server.embeddings import embed
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from pathlib import Path

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def retrieve(query: str, top_k: int = 5, chroma_path: Path = Path('./chroma_db')) -> List[str]:
    """
    Retrieve relevant chunks. Uses HyDE:
    1. Generate hypothetical answer to query (LLM)
    2. Embed hypothetical answer
    3. Retrieve docs similar to hypothetical
    """
    # HyDE: if GROQ_API_KEY isn't available (common inside a spawned MCP subprocess),
    # fall back to using the raw query as the "hypothetical doc" so retrieval still works.
    api_key = os.getenv("GROQ_API_KEY") or ""
    model_name = os.getenv("MODEL_NAME") or "llama-3.3-70b-versatile"

    hypo_doc = query
    if api_key:
        try:
            llm = Groq(api_key=api_key)
            response = llm.chat.completions.create(
                model=str(model_name),
                messages=[{"role": "user", "content": query}],
            )
            hypo_doc = response.choices[0].message.content or query
        except Exception:
            # Retrieval fallback (still useful for demo and avoids hard failure)
            hypo_doc = query

    vector = embed([hypo_doc])[0]

    embeddings = HuggingFaceEmbeddings(model_name=_MODEL_NAME)
    vector_store = Chroma(
        collection_name='RAG-embedder',
        embedding_function=embeddings,
        persist_directory=str(chroma_path)
    )

    context = vector_store.similarity_search_by_vector(vector, top_k)

    return [text.page_content for text in context]