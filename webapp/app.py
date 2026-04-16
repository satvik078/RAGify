import os
import warnings
import logging
import sqlite3
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ── Load .env variables ───────────────────────────────────────────────────
load_dotenv()

# ── Suppress noisy RAG/pypdf warnings ─────────────────────────────────────
warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality")
warnings.filterwarnings("ignore", message="Ignoring wrong pointing object")
warnings.filterwarnings("ignore", message="Accessing `__path__`")
logging.getLogger("pypdf._reader").setLevel(logging.ERROR)

app = Flask(__name__)
app.secret_key = "your-secret-key-change-in-production"

DATABASE      = os.path.join(os.path.dirname(__file__), "users.db")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploaded_docs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}


# ─────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables and seed the default admin account."""
    with app.app_context():
        db = get_db()
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                email       TEXT    NOT NULL UNIQUE,
                password    TEXT    NOT NULL,
                role        TEXT    NOT NULL DEFAULT 'user',
                created_at  TEXT    NOT NULL,
                last_login  TEXT,
                usage_count INTEGER NOT NULL DEFAULT 0,
                is_active   INTEGER NOT NULL DEFAULT 1
            );
        """)
        existing = db.execute(
            "SELECT id FROM users WHERE email = ?", ("admin@admin.com",)
        ).fetchone()
        if not existing:
            db.execute(
                """INSERT INTO users (name, email, password, role, created_at)
                   VALUES (?, ?, ?, 'admin', ?)""",
                (
                    "Admin",
                    "admin@admin.com",
                    generate_password_hash("admin123"),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
        db.commit()


# ─────────────────────────────────────────────
# AUTH DECORATORS
# ─────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Admin access only.", "danger")
            return redirect(url_for("user_dashboard"))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# ROUTES – PUBLIC
# ─────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("user_dashboard"))
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("signup.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("signup.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("signup.html")

        db = get_db()
        if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            flash("An account with that email already exists.", "danger")
            return render_template("signup.html")

        db.execute(
            """INSERT INTO users (name, email, password, role, created_at)
               VALUES (?, ?, ?, 'user', ?)""",
            (name, email, generate_password_hash(password),
             datetime.now().isoformat(timespec="seconds")),
        )
        db.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db   = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if not user or not check_password_hash(user["password"], password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        if not user["is_active"]:
            flash("Your account has been disabled. Contact admin.", "danger")
            return render_template("login.html")

        db.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), user["id"]),
        )
        db.commit()

        session["user_id"] = user["id"]
        session["name"]    = user["name"]
        session["email"]   = user["email"]
        session["role"]    = user["role"]

        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("user_dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ─────────────────────────────────────────────
# ROUTES – ADMIN
# ─────────────────────────────────────────────

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    db    = get_db()
    users = db.execute(
        """SELECT id, name, email, created_at, last_login,
                  usage_count, is_active
           FROM users
           WHERE role = 'user'
           ORDER BY created_at DESC"""
    ).fetchall()

    total_users  = len(users)
    active_users = sum(1 for u in users if u["is_active"])
    total_uses   = sum(u["usage_count"] for u in users)

    return render_template(
        "admin_dashboard.html",
        users=users,
        total_users=total_users,
        active_users=active_users,
        total_uses=total_uses,
    )


@app.route("/admin/toggle_user/<int:user_id>", methods=["POST"])
@admin_required
def toggle_user(user_id):
    db   = get_db()
    user = db.execute("SELECT is_active FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        new_status = 0 if user["is_active"] else 1
        db.execute(
            "UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id)
        )
        db.commit()
        state = "enabled" if new_status else "disabled"
        flash(f"User account {state}.", "success")
    return redirect(url_for("admin_dashboard"))


# ─────────────────────────────────────────────
# ROUTES – USER DASHBOARD & RAG CHAT
# ─────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def user_dashboard():
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
    return render_template("user_chat.html")


# ── Set / update HuggingFace API key ──────────────────────────────────────

@app.route("/api/set_api_key", methods=["POST"])
@login_required
def set_api_key():
    data    = request.get_json()
    api_key = (data or {}).get("api_key", "").strip()
    if not api_key:
        return jsonify({"error": "API key is empty."}), 400
    session["hf_api_key"] = api_key
    return jsonify({"status": "ok", "message": "API key saved for this session."})


# ── Test Supabase connection ───────────────────────────────────────────────

@app.route("/api/test_connection", methods=["POST"])
@login_required
def test_connection():
    try:
        from backend.vector_store import get_document_count
        get_document_count()
        return jsonify({"connected": True})
    except Exception as e:
        return jsonify({"connected": False, "error": str(e)})


# ── Document stats (chunks + file list) ──────────────────────────────────

@app.route("/api/doc_stats")
@login_required
def doc_stats():
    try:
        from backend.vector_store import get_document_count, list_indexed_files
        return jsonify({
            "chunk_count": get_document_count(),
            "files": list_indexed_files(),
        })
    except Exception as e:
        return jsonify({"chunk_count": 0, "files": [], "error": str(e)})


# ── Upload & index PDF documents ──────────────────────────────────────────

@app.route("/api/upload_docs", methods=["POST"])
@login_required
def upload_docs():
    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files provided."}), 400

    results   = []
    all_chunks = []

    try:
        from backend.document_loader import load_pdf
        from backend.text_splitter   import split_documents
        from backend.vector_store    import add_documents
    except ImportError as e:
        return jsonify({"error": f"Backend module not found: {e}"}), 500

    for f in files:
        filename = secure_filename(f.filename)
        if not filename.lower().endswith(".pdf"):
            results.append({"file": filename, "status": "skipped (not a PDF)"})
            continue

        save_path = os.path.join(UPLOAD_FOLDER, filename)
        f.save(save_path)

        try:
            pages      = load_pdf(save_path)
            chunks     = split_documents(pages)
            all_chunks.extend(chunks)
            results.append({"file": filename, "pages": len(pages), "chunks": len(chunks), "status": "ok"})
        except Exception as e:
            results.append({"file": filename, "status": f"error: {e}"})

    if all_chunks:
        try:
            add_documents(all_chunks)
        except Exception as e:
            return jsonify({"error": f"Failed to store in Supabase: {e}", "files": results}), 500

    return jsonify({
        "total_chunks": len(all_chunks),
        "files": results,
    })


# ── Clear all indexed documents ───────────────────────────────────────────

@app.route("/api/clear_docs", methods=["POST"])
@login_required
def clear_docs():
    try:
        from backend.vector_store import clear_vector_store
        success = clear_vector_store()
        if success:
            return jsonify({"status": "ok", "message": "All documents cleared."})
        return jsonify({"error": "clear_vector_store() returned False."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Main RAG chat endpoint ────────────────────────────────────────────────

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    data    = request.get_json()
    message = (data or {}).get("message", "").strip()

    if not message:
        return jsonify({"error": "Empty message."}), 400

    # Use hardcoded API key from environment / config
    api_key = os.environ.get("HF_API_KEY", "") or os.environ.get("HUGGINGFACE_API_KEY", "")
    if not api_key:
        try:
            from config import HUGGINGFACE_API_KEY
            api_key = HUGGINGFACE_API_KEY
        except ImportError:
            pass
    if not api_key:
        return jsonify({
            "error": "HuggingFace API key is not configured on the server."
        }), 500

    # Increment usage counter
    db = get_db()
    db.execute(
        "UPDATE users SET usage_count = usage_count + 1 WHERE id = ?",
        (session["user_id"],),
    )
    db.commit()

    # ── Call the RAG chain ────────────────────────────────────────────────
    try:
        from backend.rag_chain import ask

        result  = ask(question=message, api_key=api_key, k=5)
        answer  = result.get("answer", "No answer returned.")
        sources = result.get("source_documents", [])

        return jsonify({"response": answer, "sources": sources})

    except Exception as e:
        return jsonify({"error": f"Model error: {str(e)}"}), 500


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("─" * 55)
    print("  AI Platform (RAG) running at http://localhost:5000")
    print("  Default admin → admin@admin.com  /  admin123")
    print("─" * 55)
    app.run(debug=True, port=5000, use_reloader=False)
