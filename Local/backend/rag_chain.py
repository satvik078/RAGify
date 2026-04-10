"""
End-to-end RAG chain.
Retriever → Stuff documents into prompt → Mistral generates answer with sources.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.retrieval import create_retrieval_chain

from backend.vector_store import get_retriever
from backend.llm import get_llm

# ── System prompt ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an intelligent assistant that answers questions using company documents.

RULES:
1. Use ONLY the provided context to formulate your answer.
2. If the context does not contain enough information, say:
   "I don't have enough information in the uploaded documents to answer this."
3. Always cite the source document name and page number when available.
4. Be concise but thorough. Use bullet points for multi-part answers.
5. Never make up information that is not in the context.

CONTEXT:
{context}
"""

USER_PROMPT = "{input}"


def build_rag_chain(api_key: str | None = None, k: int = 5):
    """
    Build and return a retrieval-augmented generation chain.

    Returns a chain that accepts {"input": "user question"} and returns
    {"input": ..., "answer": ..., "context": [Document, ...]}.
    """
    # 1. Retriever
    retriever = get_retriever(k=k)

    # 2. LLM
    llm = get_llm(api_key=api_key)

    # 3. Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])

    # 4. Combine-documents chain (stuff strategy)
    combine_chain = create_stuff_documents_chain(llm=llm, prompt=prompt)

    # 5. Full retrieval chain
    rag_chain = create_retrieval_chain(retriever=retriever, combine_docs_chain=combine_chain)

    return rag_chain


def ask(question: str, api_key: str | None = None, k: int = 5) -> dict:
    """
    Convenience wrapper: ask a question and get back the answer + source docs.

    Returns:
        {
            "answer": str,
            "source_documents": [{"content": str, "source": str, "page": int}, ...]
        }
    """
    chain = build_rag_chain(api_key=api_key, k=k)
    result = chain.invoke({"input": question})

    # Extract clean source info
    sources = []
    for doc in result.get("context", []):
        sources.append({
            "content": doc.page_content[:300] + ("..." if len(doc.page_content) > 300 else ""),
            "source": doc.metadata.get("source_file", doc.metadata.get("source", "Unknown")),
            "page": doc.metadata.get("page", "N/A"),
        })

    return {
        "answer": result.get("answer", "No answer generated."),
        "source_documents": sources,
    }
