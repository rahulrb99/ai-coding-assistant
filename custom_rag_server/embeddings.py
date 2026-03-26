"""
Embeddings — Person 5
sentence-transformers/all-MiniLM-L6-v2
"""
from typing import List
from langchain_huggingface import HuggingFaceEmbeddings


def embed(texts: List[str]) -> List[List[float]]:
    """Embed texts. Return list of vectors."""
    # TODO: HuggingFaceEmbeddings
    vectors = HuggingFaceEmbeddings.em
    pass
