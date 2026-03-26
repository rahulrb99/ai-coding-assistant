"""
Embeddings — Person 5
sentence-transformers/all-MiniLM-L6-v2
"""
from typing import List
from langchain_huggingface import HuggingFaceEmbeddings


_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_embeddings_model = None


def _get_model() -> HuggingFaceEmbeddings:
    global _embeddings_model
    if _embeddings_model is None:
        _embeddings_model = HuggingFaceEmbeddings(model_name=_MODEL_NAME)
    return _embeddings_model


def embed(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts. Returns one vector per text."""
    return _get_model().embed_documents(texts)