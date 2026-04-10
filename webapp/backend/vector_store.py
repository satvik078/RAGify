"""
Supabase pgvector-backed vector store.
Handles document storage, retrieval, and collection management.
"""

import uuid
import os
from typing import List

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from supabase.client import create_client, Client
from dotenv import load_dotenv

from backend.embeddings import get_embeddings


# ── Load environment variables ───────────────────────────────────────────
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_TABLE_NAME = os.getenv("SUPABASE_TABLE_NAME", "documents")
SUPABASE_QUERY_NAME = os.getenv("SUPABASE_QUERY_NAME", "match_documents")
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", 5))


# ── Supabase client ──────────────────────────────────────────────────────

def _get_supabase_client() -> Client:
    """Create and return a Supabase client."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError(
            "❌ Missing Supabase credentials.\n"
            "Make sure SUPABASE_URL and SUPABASE_SERVICE_KEY are set in your .env file."
        )
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ── Insert documents ─────────────────────────────────────────────────────

def add_documents(docs: List[Document]) -> None:
    """Embed and insert a list of Document chunks into Supabase."""
    if not docs:
        return

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

    # Insert in batches (safe for large uploads)
    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i: i + batch_size]
        client.table(SUPABASE_TABLE_NAME).insert(batch).execute()


# ── Custom retriever using direct RPC ────────────────────────────────────

class SupabaseRetriever(BaseRetriever):
    k: int = RETRIEVAL_K

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(self, query: str, **kwargs) -> List[Document]:
        embeddings_model = get_embeddings()
        query_vector = embeddings_model.embed_query(query)

        client = _get_supabase_client()

        try:
            response = client.rpc(
                SUPABASE_QUERY_NAME,
                {
                    "query_embedding": query_vector,
                    "match_count": self.k,
                    "filter": {},
                },
            ).execute()
        except Exception as e:
            print("❌ Supabase RPC Error:", e)
            return []

        documents = []
        for row in response.data or []:
            documents.append(
                Document(
                    page_content=row.get("content", ""),
                    metadata=row.get("metadata", {}),
                )
            )

        return documents


def get_retriever(k: int = RETRIEVAL_K) -> SupabaseRetriever:
    return SupabaseRetriever(k=k)


# ── Utility functions ────────────────────────────────────────────────────

def list_indexed_files() -> List[str]:
    try:
        client = _get_supabase_client()
        response = client.table(SUPABASE_TABLE_NAME).select("metadata").execute()

        filenames = set()
        for row in response.data or []:
            meta = row.get("metadata") or {}
            name = meta.get("source_file") or meta.get("source", "")
            if name:
                filenames.add(name)

        return sorted(filenames)

    except Exception as e:
        print("❌ list_indexed_files error:", e)
        return []


def get_document_count() -> int:
    try:
        client = _get_supabase_client()
        response = client.table(SUPABASE_TABLE_NAME).select("id", count="exact").execute()
        return response.count or 0

    except Exception as e:
        print("❌ get_document_count error:", e)
        return 0


def clear_vector_store() -> bool:
    try:
        client = _get_supabase_client()

        client.table(SUPABASE_TABLE_NAME).delete().neq(
            "id", "00000000-0000-0000-0000-000000000000"
        ).execute()

        return True

    except Exception as e:
        print("❌ Error clearing vector store:", e)
        return False