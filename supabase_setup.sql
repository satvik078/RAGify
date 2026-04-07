-- =============================================================
--  Run this in your Supabase SQL Editor (one-time setup)
--  Project → SQL Editor → New Query → Paste & Run
-- =============================================================

-- 1. Enable the pgvector extension
create extension if not exists vector;

-- 2. Drop old table if it exists (uses bigserial id, incompatible with LangChain)
drop table if exists documents;

-- 3. Create the documents table with UUID id (required by LangChain)
--    384 dimensions = output size of all-MiniLM-L6-v2
create table documents (
  id         uuid primary key default gen_random_uuid(),
  content    text,
  metadata   jsonb,
  embedding  vector(384)
);

-- 4. Create an index for fast similarity search
create index documents_embedding_idx
  on documents
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- 5. Create the similarity-search function used by LangChain
create or replace function match_documents (
  query_embedding vector(384),
  match_count     int     default 5,
  filter          jsonb   default '{}'::jsonb
)
returns table (
  id         uuid,
  content    text,
  metadata   jsonb,
  similarity float
)
language plpgsql
as $$
#variable_conflict use_column
begin
  return query
  select
    id,
    content,
    metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where metadata @> filter
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;
