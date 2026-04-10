"""
Text splitter using LangChain's RecursiveCharacterTextSplitter.
Chunks documents while preserving metadata.
"""

from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import CHUNK_SIZE, CHUNK_OVERLAP


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    """Return a configured text splitter instance."""
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def split_documents(documents: List[Document]) -> List[Document]:
    """Split a list of Documents into smaller chunks."""
    splitter = get_text_splitter()
    return splitter.split_documents(documents)
