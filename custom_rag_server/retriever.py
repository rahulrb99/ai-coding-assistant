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


def retrieve(query: str, top_k: int = 5, chroma_path: Path = Path('./chroma_db')) -> List[str]:
    """
    Retrieve relevant chunks. Uses HyDE:
    1. Generate hypothetical answer to query (LLM)
    2. Embed hypothetical answer
    3. Retrieve docs similar to hypothetical
    """
    # TODO: HyDE implementation
    # TODO: Return top_k chunks
    llm = Groq(api_key=os.getenv('GROQ_API_KEY'))

    response = llm.chat.completions.create(
        model=str(os.getenv('MODEL_NAME')),
        messages=[{'role': 'user', 'content': f'{query}'}]
    )
    
    hypo_doc = response.choices[0].message.content or ""

    vector = embed([hypo_doc])[0]

    embeddings = HuggingFaceEmbeddings()
    vector_store = Chroma(
        collection_name='RAG-embedder',
        embedding_function=embeddings,
        persist_directory=str(chroma_path)
    )

    context = vector_store.similarity_search_by_vector(vector, top_k)

    return [text.page_content for text in context]