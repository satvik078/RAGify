"""
Supabase pgvector-backed vector store.
Handles document storage, retrieval, and collection management.

Uses direct Supabase RPC calls for retrieval (bypasses broken
langchain-community SupabaseVectorStore.params API on supabase v2.x).
"""

import uuid
from typing import List

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from supabase.client import create_client, Client

from config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    SUPABASE_TABLE_NAME,
    SUPABASE_QUERY_NAME,
    RETRIEVAL_K,
)
from backend.embeddings import get_embeddings


# ── Supabase client ──────────────────────────────────────────────────────

def _get_supabase_client() -> Client:
    """Create and return a Supabase client."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in your .env file. "
            "See .env.example for reference."
        )
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ── Insert documents ─────────────────────────────────────────────────────

def add_documents(docs: List[Document]) -> None:
    """Embed and insert a list of Document chunks into Supabase."""
    client = _get_supabase_client()
    embeddings_model = get_embeddings()

    texts = [doc.page_content for doc in docs]
    metadatas = [doc.metadata for doc in docs]
    vectors = embeddings_model.embed_documents(texts)

    rows = []
    for text, meta, vec in zip(texts, metadatas, vectors):
        rows.append({
            "id": str(uuid.uuid4()),
            "content": text,
            "metadata": meta,
            "embedding": vec,
        })

    # Insert in batches of 500
    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        client.table(SUPABASE_TABLE_NAME).insert(batch).execute()


# ── Custom retriever using direct RPC ────────────────────────────────────

class SupabaseRetriever(BaseRetriever):
    """
    A LangChain-compatible retriever that calls the Supabase
    match_documents RPC function directly, avoiding the broken
    .params API in langchain-community's SupabaseVectorStore.
    """

    k: int = RETRIEVAL_K

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(self, query: str, **kwargs) -> List[Document]:
        embeddings_model = get_embeddings()
        query_vector = embeddings_model.embed_query(query)

        client = _get_supabase_client()
        response = client.rpc(
            SUPABASE_QUERY_NAME,
            {
                "query_embedding": query_vector,
                "match_count": self.k,
                "filter": {},
            },
        ).execute()

        documents = []
        for row in response.data or []:
            doc = Document(
                page_content=row.get("content", ""),
                metadata=row.get("metadata", {}),
            )
            documents.append(doc)

        return documents


def get_retriever(k: int = RETRIEVAL_K) -> SupabaseRetriever:
    """Return a LangChain retriever backed by Supabase RPC."""
    return SupabaseRetriever(k=k)


# ── Utility functions ────────────────────────────────────────────────────

def list_indexed_files() -> List[str]:
    """Query Supabase for unique source filenames already indexed."""
    try:
        client = _get_supabase_client()
        response = (
            client.table(SUPABASE_TABLE_NAME)
            .select("metadata")
            .execute()
        )
        filenames = set()
        for row in response.data:
            meta = row.get("metadata") or {}
            name = meta.get("source_file") or meta.get("source", "")
            if name:
                filenames.add(name)
        return sorted(filenames)
    except Exception:
        return []


def get_document_count() -> int:
    """Return the total number of chunks stored in Supabase."""
    try:
        client = _get_supabase_client()
        response = (
            client.table(SUPABASE_TABLE_NAME)
            .select("id", count="exact")
            .execute()
        )
        return response.count or 0
    except Exception:
        return 0


def clear_vector_store() -> bool:
    """Delete ALL rows from the documents table. Returns True on success."""
    try:
        client = _get_supabase_client()
        # Use a filter that matches all UUID rows
        # '00000000-0000-0000-0000-000000000000' is the nil UUID — no real row has it
        client.table(SUPABASE_TABLE_NAME).delete().neq(
            "id", "00000000-0000-0000-0000-000000000000"
        ).execute()
        return True
    except Exception as e:
        print(f"Error clearing vector store: {e}")
        return False
