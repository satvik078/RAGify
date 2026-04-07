"""
Central configuration for the RAG system.
All tuneable constants and paths live here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── HuggingFace ──────────────────────────────────────────────────────────
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# ── Supabase ─────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_TABLE_NAME = os.getenv("SUPABASE_TABLE_NAME", "documents")
SUPABASE_QUERY_NAME = os.getenv("SUPABASE_QUERY_NAME", "match_documents")

# ── Chunking ─────────────────────────────────────────────────────────────
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# ── Retrieval ────────────────────────────────────────────────────────────
RETRIEVAL_K = 5

# ── LLM Generation ──────────────────────────────────────────────────────
MAX_NEW_TOKENS = 512
TEMPERATURE = 0.1
