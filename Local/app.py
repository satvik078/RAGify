"""
RAG System — Streamlit Frontend
Premium UI with dark theme, chat interface, document management, and source citations.
"""

import warnings
import logging

# Suppress known harmless warnings
warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality")
warnings.filterwarnings("ignore", message="Ignoring wrong pointing object")
warnings.filterwarnings("ignore", message="Accessing `__path__`")
logging.getLogger("pypdf._reader").setLevel(logging.ERROR)
logging.getLogger("streamlit.watcher.local_sources_watcher").setLevel(logging.ERROR)

import streamlit as st
import time

# ── Page config (MUST be first Streamlit call) ───────────────────────────
st.set_page_config(
    page_title="RAG Document Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for premium look ──────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Global ── */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* ── Header ── */
    .main-header {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    .main-header h1 {
        color: #ffffff;
        font-size: 2rem;
        font-weight: 700;
        margin: 0 0 0.3rem 0;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: rgba(255, 255, 255, 0.6);
        font-size: 0.95rem;
        margin: 0;
    }

    /* ── Stat cards ── */
    .stat-card {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    .stat-card .stat-value {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .stat-card .stat-label {
        color: rgba(255, 255, 255, 0.5);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.3rem;
    }

    /* ── Chat messages ── */
    .chat-msg-user {
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: #fff;
        padding: 1rem 1.4rem;
        border-radius: 16px 16px 4px 16px;
        margin: 0.5rem 0;
        max-width: 80%;
        margin-left: auto;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .chat-msg-assistant {
        background: rgba(30, 30, 50, 0.6);
        border: 1px solid rgba(99, 102, 241, 0.15);
        color: #e2e8f0;
        padding: 1rem 1.4rem;
        border-radius: 16px 16px 16px 4px;
        margin: 0.5rem 0;
        max-width: 85%;
        font-size: 0.95rem;
        line-height: 1.6;
    }

    /* ── Source cards ── */
    .source-card {
        background: rgba(15, 15, 35, 0.5);
        border: 1px solid rgba(99, 102, 241, 0.15);
        border-left: 3px solid #818cf8;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin: 0.4rem 0;
        font-size: 0.82rem;
        color: #94a3b8;
    }
    .source-card strong {
        color: #c084fc;
    }

    /* ── Sidebar styling ── */
    .sidebar-section {
        background: rgba(15, 15, 35, 0.4);
        border: 1px solid rgba(99, 102, 241, 0.1);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .sidebar-section h3 {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #818cf8;
        margin-bottom: 0.8rem;
        font-weight: 600;
    }

    /* ── Status badge ── */
    .status-connected {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .status-disconnected {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    /* ── File list ── */
    .file-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.7rem;
        background: rgba(99, 102, 241, 0.06);
        border-radius: 8px;
        margin: 0.3rem 0;
        font-size: 0.85rem;
        color: #c4b5fd;
    }

    /* ── Empty state ── */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        color: rgba(255, 255, 255, 0.3);
    }
    .empty-state .emoji {
        font-size: 4rem;
        margin-bottom: 1rem;
    }
    .empty-state h3 {
        font-size: 1.3rem;
        margin-bottom: 0.5rem;
        color: rgba(255, 255, 255, 0.5);
    }
    .empty-state p {
        font-size: 0.9rem;
    }

    /* ── Hide Streamlit defaults ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: visible;}

    /* ── Button tweaks ── */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 0.5rem 1.2rem;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    }

    /* ── Divider ── */
    .section-divider {
        border: none;
        border-top: 1px solid rgba(99, 102, 241, 0.1);
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ───────────────────────────────────────────────

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "documents_indexed" not in st.session_state:
    st.session_state.documents_indexed = False

if "indexing_in_progress" not in st.session_state:
    st.session_state.indexing_in_progress = False

if "hf_api_key" not in st.session_state:
    st.session_state.hf_api_key = ""

if "supabase_connected" not in st.session_state:
    st.session_state.supabase_connected = False


# ── Helper: check Supabase connection ────────────────────────────────────

def check_supabase_connection() -> bool:
    """Test if Supabase credentials are valid."""
    try:
        from backend.vector_store import get_document_count
        get_document_count()
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🧠 RAG Assistant")
    st.markdown("---")

    # ── API Key ──────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("<h3>🔑 API Configuration</h3>", unsafe_allow_html=True)

    hf_key = st.text_input(
        "API Key",
        type="password",
        value=st.session_state.hf_api_key,
        placeholder="hf_... or sk_...",
        help="Get your free key at huggingface.co/settings/tokens",
    )
    if hf_key:
        st.session_state.hf_api_key = hf_key

    # Connection status
    if st.button("🔄 Test Connection", use_container_width=True):
        with st.spinner("Testing Supabase connection..."):
            connected = check_supabase_connection()
            st.session_state.supabase_connected = connected

    if st.session_state.supabase_connected:
        st.markdown('<span class="status-connected">● Supabase Connected</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-disconnected">● Not Connected</span>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Document Upload ──────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("<h3>📁 Document Manager</h3>", unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Upload company PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload one or more PDF documents to index",
    )

    if uploaded_files and st.button("⚡ Index Documents", use_container_width=True, type="primary"):
        st.session_state.indexing_in_progress = True

        progress_bar = st.progress(0, text="Starting...")
        status_text = st.empty()

        try:
            from backend.document_loader import save_uploaded_file, load_pdf
            from backend.text_splitter import split_documents
            from backend.vector_store import add_documents

            all_chunks = []
            total_files = len(uploaded_files)

            for i, uploaded_file in enumerate(uploaded_files):
                # Save
                status_text.markdown(f"📄 Processing **{uploaded_file.name}**...")
                progress_bar.progress((i) / total_files, text=f"Loading {uploaded_file.name}...")

                file_path = save_uploaded_file(uploaded_file)

                # Load
                pages = load_pdf(file_path)
                status_text.markdown(f"📄 **{uploaded_file.name}** — {len(pages)} pages loaded")

                # Chunk
                progress_bar.progress((i + 0.5) / total_files, text=f"Chunking {uploaded_file.name}...")
                chunks = split_documents(pages)
                all_chunks.extend(chunks)

            # Embed & store
            progress_bar.progress(0.9, text="Embedding & storing in Supabase...")
            status_text.markdown(f"🧬 Embedding **{len(all_chunks)} chunks** into Supabase...")
            add_documents(all_chunks)

            progress_bar.progress(1.0, text="Done!")
            status_text.markdown(
                f"✅ Indexed **{total_files} file(s)** → **{len(all_chunks)} chunks** stored"
            )
            st.session_state.documents_indexed = True
            st.session_state.supabase_connected = True
            time.sleep(1)

        except Exception as e:
            st.error(f"❌ Indexing failed: {e}")

        finally:
            st.session_state.indexing_in_progress = False

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Indexed files ────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("<h3>📊 Indexed Documents</h3>", unsafe_allow_html=True)

    try:
        from backend.vector_store import list_indexed_files, get_document_count

        indexed = list_indexed_files()
        count = get_document_count()

        if indexed:
            st.markdown(f"**{count}** chunks from **{len(indexed)}** file(s)")
            for fname in indexed:
                st.markdown(f'<div class="file-item">📄 {fname}</div>', unsafe_allow_html=True)
        else:
            st.caption("No documents indexed yet.")

    except Exception:
        st.caption("Connect to Supabase to see indexed docs.")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Danger zone ──────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("🗑️ Danger Zone"):
        if st.button("Clear All Documents", type="secondary", use_container_width=True):
            try:
                from backend.vector_store import clear_vector_store
                if clear_vector_store():
                    st.success("All documents cleared!")
                    st.session_state.chat_history = []
                    st.session_state.documents_indexed = False
                    st.rerun()
                else:
                    st.error("Failed to clear documents.")
            except Exception as e:
                st.error(f"Error: {e}")

        if st.button("Clear Chat History", type="secondary", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════
#  MAIN AREA
# ══════════════════════════════════════════════════════════════════════════

# ── Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🧠 RAG Document Assistant</h1>
    <p>Ask questions about your company documents · Powered by Qwen-7B + Supabase pgvector</p>
</div>
""", unsafe_allow_html=True)

# ── Stats row ────────────────────────────────────────────────────────────
try:
    from backend.vector_store import get_document_count, list_indexed_files
    _chunk_count = get_document_count()
    _file_count = len(list_indexed_files())
except Exception:
    _chunk_count = 0
    _file_count = 0

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
    <div class="stat-card">
        <p class="stat-value">{_file_count}</p>
        <p class="stat-label">Documents</p>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="stat-card">
        <p class="stat-value">{_chunk_count}</p>
        <p class="stat-label">Chunks Indexed</p>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="stat-card">
        <p class="stat-value">{len(st.session_state.chat_history) // 2}</p>
        <p class="stat-label">Questions Asked</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ── Chat history display ────────────────────────────────────────────────

if not st.session_state.chat_history:
    st.markdown("""
    <div class="empty-state">
        <div class="emoji">💬</div>
        <h3>Start a conversation</h3>
        <p>Upload PDF documents in the sidebar, then ask questions about their content.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in st.session_state.chat_history:
        role = msg["role"]
        with st.chat_message(role, avatar="🧑‍💼" if role == "user" else "🧠"):
            st.markdown(msg["content"])

            # Show sources for assistant messages
            if role == "assistant" and "sources" in msg and msg["sources"]:
                with st.expander(f"📄 Sources ({len(msg['sources'])} references)", expanded=False):
                    for src in msg["sources"]:
                        st.markdown(
                            f'<div class="source-card">'
                            f'<strong>📄 {src["source"]}</strong> · Page {src["page"]}<br/>'
                            f'{src["content"]}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

# ── Chat input ───────────────────────────────────────────────────────────

if prompt := st.chat_input("Ask a question about your documents..."):
    # Validate prerequisites
    if not st.session_state.hf_api_key:
        st.error("⚠️ Please enter your HuggingFace API key in the sidebar.")
        st.stop()

    # Add user message
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant", avatar="🧠"):
        with st.spinner("🔍 Searching documents & generating answer..."):
            try:
                from backend.rag_chain import ask

                result = ask(
                    question=prompt,
                    api_key=st.session_state.hf_api_key,
                    k=5,
                )

                answer = result["answer"]
                sources = result["source_documents"]

                # Display answer
                st.markdown(answer)

                # Display sources
                if sources:
                    with st.expander(f"📄 Sources ({len(sources)} references)", expanded=False):
                        for src in sources:
                            st.markdown(
                                f'<div class="source-card">'
                                f'<strong>📄 {src["source"]}</strong> · Page {src["page"]}<br/>'
                                f'{src["content"]}'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                # Save to history
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                })

            except Exception as e:
                error_msg = f"❌ Error generating response: {str(e)}"
                st.error(error_msg)
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": error_msg,
                    "sources": [],
                })
