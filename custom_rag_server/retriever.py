"""
RAG Retriever — Person 5
HyDE: generate hypothetical answer, embed, retrieve similar chunks.
"""
from typing import List


def retrieve(query: str, top_k: int = 5) -> List[str]:
    """
    Retrieve relevant chunks. Uses HyDE:
    1. Generate hypothetical answer to query (LLM)
    2. Embed hypothetical answer
    3. Retrieve docs similar to hypothetical
    """
    # TODO: HyDE implementation
    # TODO: Return top_k chunks
    pass
