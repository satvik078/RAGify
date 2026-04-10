"""
PDF document loader using PyPDF via LangChain.
Extracts text from uploaded PDFs and attaches metadata.
"""

import os
import time
from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from config import UPLOAD_DIR


def save_uploaded_file(uploaded_file) -> Path:
    """Save a Streamlit UploadedFile to the uploads directory and return its path."""
    file_path = UPLOAD_DIR / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


def load_pdf(file_path: str | Path) -> List[Document]:
    """
    Load a single PDF and return a list of Documents (one per page).
    Each Document has metadata: source filename, page number, and upload timestamp.
    """
    file_path = Path(file_path)
    loader = PyPDFLoader(str(file_path))
    pages = loader.load()

    # Enrich metadata
    for page in pages:
        page.metadata["source_file"] = file_path.name
        page.metadata["upload_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

    return pages


def load_all_pdfs(directory: str | Path | None = None) -> List[Document]:
    """Load every PDF found in the given directory (defaults to UPLOAD_DIR)."""
    directory = Path(directory) if directory else UPLOAD_DIR
    all_docs: List[Document] = []

    for pdf_file in sorted(directory.glob("*.pdf")):
        all_docs.extend(load_pdf(pdf_file))

    return all_docs
