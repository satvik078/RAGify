"""
Embedding model factory.
Uses HuggingFace sentence-transformers/all-MiniLM-L6-v2 (runs locally, free).
"""

from langchain_huggingface import HuggingFaceEmbeddings

from config import EMBEDDING_MODEL


def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Return a HuggingFace embedding model.
    all-MiniLM-L6-v2 produces 384-dimensional vectors and runs locally
    (no API key needed for embeddings).
    """
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
